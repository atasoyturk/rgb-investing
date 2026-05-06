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
        public int CurrentPage { get; set; } = 1;
        public int PageSize    { get; set; } = 15;
        public int TotalPages  { get; set; }
        public List<SignalModel> AllSignals { get; set; } = new();
        
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
            bool showPortfolio = false,
            int page = 1)
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

                if (SignalsTable != null)
                {
                    var tickers = SignalsTable.Signals.Select(s => s.Ticker).ToList();
                    var predictions = await _db.Predictions
                        .Where(p => p.Market == market && tickers.Contains(p.Ticker))
                        .OrderByDescending(p => p.PredictedDate)
                        .ToListAsync();

                    foreach (var sig in SignalsTable.Signals)
                    {
                        var pred = predictions.FirstOrDefault(p => p.Ticker == sig.Ticker);
                        if (pred != null && sig.LastPrice.HasValue && pred.PriceAtSignal > 0)
                        {
                            sig.SignalPrice = pred.PriceAtSignal;
                            sig.PriceChange = Math.Round(
                                (sig.LastPrice.Value - pred.PriceAtSignal) / pred.PriceAtSignal * 100, 2);
                        }
                    }

                    AllSignals = SignalsTable.Signals.ToList();

                    CurrentPage = page;
                    TotalPages  = (int)Math.Ceiling(SignalsTable.Signals.Count / (double)PageSize);
                    SignalsTable.Signals = SignalsTable.Signals
                        .OrderByDescending(x => x.Confidence)
                        .Skip((page - 1) * PageSize)
                        .Take(PageSize)
                        .ToList();
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
