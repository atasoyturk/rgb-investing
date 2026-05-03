using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using RgbFinanceWeb.Data;

namespace RgbFinanceWeb.Pages
{
    public class LoginModel : PageModel
    {
        private readonly SignInManager<AppUser> _signInManager;
        private readonly UserManager<AppUser>  _userManager;


        public string? ErrorMessage { get; set; }

        public LoginModel(SignInManager<AppUser> signInManager, UserManager<AppUser> userManager)
        {
            _signInManager = signInManager;
            _userManager = userManager;
        }

        public void OnGet() { }

        public async Task<IActionResult> OnPostAsync(string email, string password)
        {
            var result = await _signInManager.PasswordSignInAsync(
                email, password, isPersistent: false, lockoutOnFailure: false);

            if (result.Succeeded)
            {
                var user = await _userManager.FindByEmailAsync(email);
                if (user != null && await _userManager.IsInRoleAsync(user, "Admin"))
                {
                    var has2FA = await _userManager.GetTwoFactorEnabledAsync(user);
                    if (!has2FA)
                        return RedirectToPage("/EnableTwoFactor");
                }
                return RedirectToPage("/Index");
            }

            if (result.RequiresTwoFactor)
                return RedirectToPage("/LoginTwoFactor", new { email });

            ErrorMessage = "Invalid email or password.";
            return Page();
        }
    }
}