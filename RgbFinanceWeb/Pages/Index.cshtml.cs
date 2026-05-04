using Microsoft.AspNetCore.Mvc.RazorPages;
using System.Text.Json;
using RgbFinanceWeb.Models;

using Microsoft.EntityFrameworkCore;
using RgbFinanceWeb.Data;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace RgbFinanceWeb.Pages
{
    public class IndexModel : PageModel
    {
        private readonly IHttpClientFactory _httpClientFactory;
        private readonly ILogger<IndexModel> _logger;

        private readonly AppDbContext _db;
        private readonly UserManager<AppUser> _userManager;

        public SignalsTableModel? SignalsTable { get; set; }
        public HealthModel?       Health       { get; set; }
        public string?            ErrorMessage { get; set; }

        public string SelectedMarket { get; set; } = "SP500";  

        public string SelectedSignal { get; set; } = "ALL";
        public int    MinTrust       { get; set; } = 0;

        public bool ShowPortfolio { get; set; } = false;

        public string? ThresholdLabel { get; set; }

        public IndexModel(IHttpClientFactory httpClientFactory, ILogger<IndexModel> logger, 
                  AppDbContext db, UserManager<AppUser> userManager)
        {
            _httpClientFactory = httpClientFactory;
            _logger            = logger;
            _db                = db;
            _userManager       = userManager;
        }

        public async Task<IActionResult> OnGetAsync(
            string market = "SP500", 
            string signal = "ALL", 
            int minTrust = 0, 
            bool showPortfolio = false)
        {
            if (!User.Identity?.IsAuthenticated ?? true)
                return RedirectToPage("/Landing");

            var client  = _httpClientFactory.CreateClient("FinanceApi");
            var options = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true,
                PropertyNamingPolicy        = JsonNamingPolicy.SnakeCaseLower,
            };

            try
            {
                var healthResponse = await client.GetAsync("health");
                if (healthResponse.IsSuccessStatusCode)
                    Health = JsonSerializer.Deserialize<HealthModel>(
                        await healthResponse.Content.ReadAsStringAsync(), options);
                
                SelectedMarket = market;
                SelectedSignal = signal;
                MinTrust       = minTrust;
                ShowPortfolio = showPortfolio;
                
                var signalsResponse = await client.GetAsync($"signals?market={market}");
                if (signalsResponse.IsSuccessStatusCode)
                    SignalsTable = JsonSerializer.Deserialize<SignalsTableModel>(
                        await signalsResponse.Content.ReadAsStringAsync(), options);
                
                var user = await _userManager.GetUserAsync(User);
                if (user != null && SignalsTable != null)
                {
                    var userTickers = await _db.UserTickers
                        .Where(t => t.UserId == user.Id && t.Market == market)
                        .Select(t => t.Symbol)
                        .ToListAsync();

                    if (showPortfolio && userTickers.Any())
                        SignalsTable.Signals = SignalsTable.Signals
                            .Where(s => userTickers.Contains(s.Ticker))
                            .ToList();
                }
                
                if (SignalsTable != null)
                {
                    if (signal != "ALL")
                        SignalsTable.Signals = SignalsTable.Signals
                            .Where(s => s.Signal == signal).ToList();

                    if (minTrust > 0)
                        SignalsTable.Signals = SignalsTable.Signals
                            .Where(s => s.Confidence * 100 >= minTrust).ToList();
                }

                var thresholdResponse = await client.GetAsync($"threshold?market={market}");
                if (thresholdResponse.IsSuccessStatusCode)
                {
                    var thresholdJson = JsonSerializer.Deserialize<JsonElement>(
                        await thresholdResponse.Content.ReadAsStringAsync(), options);
                    ThresholdLabel = thresholdJson.GetProperty("label").GetString();
                }
            
            }
            catch (HttpRequestException)  { ErrorMessage = "Cannot connect to Python API. Is FastAPI running?"; }
            catch (TaskCanceledException) { ErrorMessage = "Request timed out."; }

            return Page();
        }
    }
}
