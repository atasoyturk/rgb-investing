using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;


namespace RgbFinanceWeb.Pages
{
    [Authorize(Roles = "Admin")]
    public class TrainModel : PageModel
    {
        private readonly IHttpClientFactory _httpClientFactory;
        public string? JobId { get; set; }

        public TrainModel(IHttpClientFactory httpClientFactory)
        {
            _httpClientFactory = httpClientFactory;
        }

        public void OnGet() { }

        public async Task<IActionResult> OnPostAsync(
            string tickers, string startDate, string endDate,
            int windowSize, int futureDays, int stride, string name, string market, bool fineTune = false)
        {
            var client = _httpClientFactory.CreateClient("FinanceApi");

            var body = JsonSerializer.Serialize(new
            {
                name,
                market,
                tickers = tickers?.Split(',').Select(t => t.Trim()).ToList() ?? new List<string>(),
                start_date  = startDate,
                end_date    = endDate,
                window_size = windowSize,
                future_days = futureDays,
                fine_tune = fineTune,
                stride
            });

            var response = await client.PostAsync("train",
                new StringContent(body, Encoding.UTF8, "application/json"));

            if (response.IsSuccessStatusCode)
            {
                var json = await response.Content.ReadAsStringAsync();
                var result = JsonSerializer.Deserialize<JsonElement>(json);
                JobId = result.GetProperty("job_id").GetString();
            }

            return Page();
        }
    }
}