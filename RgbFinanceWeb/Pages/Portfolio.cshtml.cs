using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;
using RgbFinanceWeb.Data;

namespace RgbFinanceWeb.Pages
{
    [Authorize]
    public class PortfolioModel : PageModel
    {
        private readonly AppDbContext         _db;
        private readonly UserManager<AppUser> _userManager;

        public List<UserTicker> Tickers    { get; set; } = new();
        public string?          SuccessMessage { get; set; }

        public PortfolioModel(AppDbContext db, UserManager<AppUser> userManager)
        {
            _db          = db;
            _userManager = userManager;
        }

        public async Task OnGetAsync()
        {
            var user = await _userManager.GetUserAsync(User);
            if (user == null) return;
            Tickers = await _db.UserTickers
                .Where(t => t.UserId == user.Id)
                .ToListAsync();
        }

        public async Task<IActionResult> OnPostAddAsync(string symbol, string market = "SP500")
        {
            var user = await _userManager.GetUserAsync(User);
            if (user == null) return RedirectToPage();
            if (!_db.UserTickers.Any(t => t.UserId == user.Id && t.Symbol == symbol))
            {
                _db.UserTickers.Add(new UserTicker { UserId = user.Id, Symbol = symbol, Market = market });
                await _db.SaveChangesAsync();
            }
            SuccessMessage = $"{symbol} added.";
            return await OnGetAsync().ContinueWith(_ => (IActionResult)Page());
        }

        public async Task<IActionResult> OnPostRemoveAsync(string symbol)
        {
            var user = await _userManager.GetUserAsync(User);
            if (user == null) return RedirectToPage();
            var ticker = await _db.UserTickers
                .FirstOrDefaultAsync(t => t.UserId == user.Id && t.Symbol == symbol);
            if (ticker != null)
            {
                _db.UserTickers.Remove(ticker);
                await _db.SaveChangesAsync();
            }
            return RedirectToPage();
        }
    }
}