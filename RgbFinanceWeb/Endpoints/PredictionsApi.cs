using Microsoft.EntityFrameworkCore;
using RgbFinanceWeb.Data;

namespace RgbFinanceWeb.Endpoints
{
    public static class PredictionsApi
    {
        public static void MapPredictionEndpoints(this WebApplication app)
        {
            app.MapPost("/api/predictions", async (
                List<PredictionDto> predictions,
                AppDbContext db) =>
            {
                foreach (var p in predictions)
                {
                    db.Predictions.Add(new Prediction
                    {
                        Ticker        = p.Ticker,
                        Market        = p.Market,
                        Signal        = p.Signal,
                        Confidence    = p.Confidence,
                        PriceAtSignal = p.PriceAtSignal,
                        PredictedDate = DateTime.Parse(p.PredictedDate),
                        TargetDate    = DateTime.Parse(p.TargetDate),
                        ActualOutcome = null,
                        ActualPrice   = null,
                    });
                }
                await db.SaveChangesAsync();
                return Results.Ok(new { saved = predictions.Count });
            });

            app.MapPost("/api/drift/check", async (string market, AppDbContext db, IHttpClientFactory factory) =>
            {
                var predictions = await db.Predictions
                    .Where(p => p.Market == market &&
                                p.TargetDate <= DateTime.Now.Date &&
                                p.ActualOutcome == null)
                    .ToListAsync();

                if (!predictions.Any())
                    return Results.Ok(new { market, checked_count = 0, accuracy = (double?)null, message = "No predictions to evaluate yet" });

                var client  = factory.CreateClient("FinanceApi");
                int correct = 0;

                foreach (var pred in predictions)
                {
                    try
                    {
                        var r = await client.GetAsync($"signals/{pred.Ticker}?market={market}");
                        if (!r.IsSuccessStatusCode) continue;

                        var json    = await r.Content.ReadAsStringAsync();
                        var signal  = System.Text.Json.JsonSerializer.Deserialize<System.Text.Json.JsonElement>(json);
                        var current = signal.GetProperty("last_price").GetDouble();

                        bool outcome      = pred.Signal == "BUY"
                            ? current > pred.PriceAtSignal
                            : current < pred.PriceAtSignal;

                        pred.ActualOutcome = outcome;
                        pred.ActualPrice   = (float)current;
                        if (outcome) correct++;
                    }
                    catch { }
                }

                await db.SaveChangesAsync();
                var accuracy = predictions.Count > 0 ? (double)correct / predictions.Count : 0;

                return Results.Ok(new {
                    market,
                    checked_count = predictions.Count,
                    correct,
                    accuracy      = Math.Round(accuracy, 4),
                    message       = accuracy < 0.45 ? "⚠️ DRIFT DETECTED" : "✓ OK"
                });
            });
        }
    }
    public record PredictionDto(
        string Ticker,
        string Market,
        string Signal,
        float  Confidence,
        float  PriceAtSignal,
        string PredictedDate,
        string TargetDate
    );
}