using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using System.Text.Json;
using RgbFinanceWeb.Models;
using Microsoft.AspNetCore.Authorization;

namespace RgbFinanceWeb.Pages
{
    [Authorize]
    public class DetailModel : PageModel
    {
        private readonly IHttpClientFactory      _httpClientFactory;
        private readonly IConfiguration          _configuration;

        public SignalModel? Signal       { get; set; }
        public string?      ErrorMessage { get; set; }
        
        [BindProperty(SupportsGet = true)]
        public string Market { get; set; } = "SP500";
        
        public string? WeightsJson { get; set; }
        public string       ApiBaseUrl   { get; private set; } = string.Empty;

        [BindProperty(SupportsGet = true)]
        public string Ticker { get; set; } = string.Empty;

        public DetailModel(IHttpClientFactory httpClientFactory, IConfiguration configuration)
        {
            _httpClientFactory = httpClientFactory;
            _configuration     = configuration;
        }

        public async Task OnGetAsync()
        {
            // Expose API base URL to the view so image src tags are not hardcoded
            ApiBaseUrl = (_configuration["ApiSettings:BaseUrl"] ?? "http://localhost:8000/").TrimEnd('/');

            if (string.IsNullOrEmpty(Ticker))
            {
                ErrorMessage = "No ticker provided.";
                return;
            }

            var client  = _httpClientFactory.CreateClient("FinanceApi");
            var options = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true,
                PropertyNamingPolicy        = JsonNamingPolicy.SnakeCaseLower,
            };

            try
            {
                var response = await client.GetAsync($"signals/{Ticker}?market={Market}");
                if (response.IsSuccessStatusCode)
                    Signal = JsonSerializer.Deserialize<SignalModel>(
                        await response.Content.ReadAsStringAsync(), options);
                else
                    ErrorMessage = $"Could not get signal for '{Ticker}'.";

                var weightsResponse = await client.GetAsync($"weights_json?market={Market}");
                if (weightsResponse.IsSuccessStatusCode)
                    WeightsJson = await weightsResponse.Content.ReadAsStringAsync();
            }
            catch (HttpRequestException) { ErrorMessage = "Cannot connect to Python API."; }
        }
    }
}
