using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using RgbFinanceWeb.Data;

namespace RgbFinanceWeb.Pages
{
    public class RegisterModel : PageModel
    {
        private readonly UserManager<AppUser>   _userManager;
        private readonly SignInManager<AppUser> _signInManager;

        public string? ErrorMessage { get; set; }

        public RegisterModel(UserManager<AppUser> userManager, SignInManager<AppUser> signInManager)
        {
            _userManager   = userManager;
            _signInManager = signInManager;
        }

        public void OnGet() { }

        public async Task<IActionResult> OnPostAsync(string email, string password, string confirmPassword)
        {
            if (password != confirmPassword)
            {
                ErrorMessage = "Passwords do not match.";
                return Page();
            }

            var user   = new AppUser { UserName = email, Email = email };
            var result = await _userManager.CreateAsync(user, password);

            if (result.Succeeded)
            {
                await _signInManager.SignInAsync(user, isPersistent: false);
                return RedirectToPage("/Index");
            }

            ErrorMessage = string.Join(" ", result.Errors.Select(e => e.Description));
            return RedirectToPage("/Portfolio");

        }
    }
}