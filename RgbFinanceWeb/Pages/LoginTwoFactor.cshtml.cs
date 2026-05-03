using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using RgbFinanceWeb.Data;

namespace RgbFinanceWeb.Pages
{
    public class LoginTwoFactorModel : PageModel
    {
        private readonly SignInManager<AppUser> _signInManager;

        public string?  Email        { get; set; }
        public string?  ErrorMessage { get; set; }

        public LoginTwoFactorModel(SignInManager<AppUser> signInManager)
        {
            _signInManager = signInManager;
        }

        public void OnGet(string email) => Email = email;

        public async Task<IActionResult> OnPostAsync(string email, string code)
        {
            var result = await _signInManager.TwoFactorAuthenticatorSignInAsync(
                code.Replace(" ", ""), isPersistent: false, rememberClient: false);

            if (result.Succeeded)
                return RedirectToPage("/Index");

            ErrorMessage = "Invalid code. Please try again.";
            Email        = email;
            return Page();
        }
    }
}