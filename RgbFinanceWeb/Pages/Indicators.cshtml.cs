using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using System.Text.Json;

namespace RgbFinanceWeb.Pages
{
    [Authorize]
    public class IndicatorsModel : PageModel
    {
        private readonly IHttpClientFactory _httpClientFactory;

        public string SelectedMarket { get; set; } = "SP500";
        public string? WeightsJson   { get; set; }
        public string? ErrorMessage  { get; set; }

        public IndicatorsModel(IHttpClientFactory httpClientFactory)
        {
            _httpClientFactory = httpClientFactory;
        }

        public async Task OnGetAsync(string market = "SP500")
        {
            SelectedMarket = market;
            var client = _httpClientFactory.CreateClient("FinanceApi");
            try
            {
                var response = await client.GetAsync($"indicators/{market}");
                if (response.IsSuccessStatusCode)
                    WeightsJson = await response.Content.ReadAsStringAsync();
                else
                    ErrorMessage = $"No model for {market}.";
            }
            catch (HttpRequestException)
            {
                ErrorMessage = "Cannot connect to Python API.";
            }
        }
    }
}