using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using RgbFinanceWeb.Data;
using Microsoft.EntityFrameworkCore;

namespace RgbFinanceWeb.Pages
{
    [Authorize]
    public class SettingsModel : PageModel
    {
        private readonly UserManager<AppUser>   _userManager;
        private readonly SignInManager<AppUser> _signInManager;
        private readonly AppDbContext           _db;

        public string?  SuccessMessage { get; set; }
        public string?  ErrorMessage   { get; set; }
        public AppUser? CurrentUser    { get; set; }

        public SettingsModel(UserManager<AppUser> userManager, SignInManager<AppUser> signInManager, AppDbContext db)
        {
            _userManager   = userManager;
            _signInManager = signInManager;
            _db            = db;
        }

        public async Task OnGetAsync()
        {
            CurrentUser = await _userManager.GetUserAsync(User);
        }

        public async Task<IActionResult> OnPostChangePasswordAsync(string currentPassword, string newPassword, string confirmPassword)
        {
            if (newPassword != confirmPassword)
            {
                ErrorMessage = "New passwords do not match.";
                CurrentUser  = await _userManager.GetUserAsync(User);
                return Page();
            }

            var user   = await _userManager.GetUserAsync(User);
            var result = await _userManager.ChangePasswordAsync(user!, currentPassword, newPassword);

            if (result.Succeeded)
            {
                await _signInManager.RefreshSignInAsync(user!);
                SuccessMessage = "Password changed successfully.";
            }
            else
            {
                ErrorMessage = string.Join(" ", result.Errors.Select(e => e.Description));
            }

            CurrentUser = user;
            return Page();
        }

        public async Task<IActionResult> OnPostDeleteAccountAsync(string confirmEmail)
        {
            var user = await _userManager.GetUserAsync(User);
            if (user == null) return RedirectToPage("/Login");

            if (user.Email != confirmEmail)
            {
                ErrorMessage = "Email does not match. Account not deleted.";
                CurrentUser  = user;
                return Page();
            }

            // Kullanıcıya ait tüm verileri sil
            var tickers     = _db.UserTickers.Where(t => t.UserId == user.Id);
            var predictions = _db.Predictions.Where(p => _db.UserTickers
                .Where(t => t.UserId == user.Id)
                .Select(t => t.Symbol)
                .Contains(p.Ticker));

            _db.UserTickers.RemoveRange(tickers);
            await _db.SaveChangesAsync();

            await _signInManager.SignOutAsync();
            await _userManager.DeleteAsync(user);

            return RedirectToPage("/Landing");
        }
    }
}