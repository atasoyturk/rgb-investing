using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using RgbFinanceWeb.Data;

namespace RgbFinanceWeb.Pages
{
    [Authorize]
    public class PerformanceModel : PageModel
    {
        private readonly AppDbContext         _db;
        private readonly UserManager<AppUser> _userManager;

        public List<UserTicker>  Portfolio    { get; set; } = new();
        public List<Prediction>  Predictions  { get; set; } = new();
        public bool              HasPortfolio { get; set; } = false;
        public double            WinRate      { get; set; } = 0;
        public double            AvgReturn    { get; set; } = 0;
        public int               TotalTrades  { get; set; } = 0;

        public PerformanceModel(AppDbContext db, UserManager<AppUser> userManager)
        {
            _db          = db;
            _userManager = userManager;
        }

        public async Task OnGetAsync()
        {
            var user = await _userManager.GetUserAsync(User);
            if (user == null) return;

            Portfolio = await _db.UserTickers
                .Where(t => t.UserId == user.Id)
                .ToListAsync();

            HasPortfolio = Portfolio.Any();
            if (!HasPortfolio) return;

            var symbols = Portfolio.Select(t => t.Symbol).ToList();

            Predictions = await _db.Predictions
                .Where(p => symbols.Contains(p.Ticker) && p.ActualOutcome != null)
                .OrderByDescending(p => p.PredictedDate)
                .ToListAsync();

            TotalTrades = Predictions.Count;

            if (TotalTrades > 0)
            {
                WinRate   = Math.Round((double)Predictions.Count(p => p.ActualOutcome == true) / TotalTrades * 100, 1);
                AvgReturn = Math.Round(Predictions
                    .Where(p => p.ActualPrice.HasValue && p.PriceAtSignal > 0)
                    .Select(p => (double)(p.ActualPrice!.Value - p.PriceAtSignal) / p.PriceAtSignal * 100)
                    .DefaultIfEmpty(0)
                    .Average(), 2);
            }
        }
    }
}