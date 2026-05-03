namespace RgbFinanceWeb.Endpoints
{
    public static class ProxyApi
    {
        public static void MapProxyEndpoints(this WebApplication app)
        {
            app.MapGet("/api/proxy/search", async (string q, IHttpClientFactory factory, IConfiguration config) =>
            {
                var apiKey   = config["Finnhub:ApiKey"];
                var client   = factory.CreateClient();
                client.BaseAddress = new Uri("https://finnhub.io/");
                var response = await client.GetAsync($"api/v1/search?q={Uri.EscapeDataString(q)}&token={apiKey}");
                var json     = await response.Content.ReadAsStringAsync();
                return Results.Content(json, "application/json");
            });

            app.MapGet("/api/proxy/train/{jobId}", async (string jobId, IHttpClientFactory factory) =>
            {
                var client   = factory.CreateClient("FinanceApi");
                var response = await client.GetAsync($"train/{jobId}");
                var json     = await response.Content.ReadAsStringAsync();
                return Results.Content(json, "application/json");
            });

            app.MapGet("/api/proxy/weights_json", async (string market, IHttpClientFactory factory) =>
            {
                var client   = factory.CreateClient("FinanceApi");
                var response = await client.GetAsync($"weights_json?market={market}");
                var json     = await response.Content.ReadAsStringAsync();
                return Results.Content(json, "application/json");
            });

            app.MapGet("/api/proxy/indicators/{market}", async (string market, IHttpClientFactory factory) =>
            {
                var client   = factory.CreateClient("FinanceApi");
                var response = await client.GetAsync($"indicators/{market}");
                var json     = await response.Content.ReadAsStringAsync();
                return Results.Content(json, "application/json");
            });

            app.MapGet("/api/proxy/model/history/{market}", async (string market, IHttpClientFactory factory) =>
            {
                var client   = factory.CreateClient("FinanceApi");
                var response = await client.GetAsync($"model/history/{market}");
                var json     = await response.Content.ReadAsStringAsync();
                return Results.Content(json, "application/json");
            });
            
        }
    }
}