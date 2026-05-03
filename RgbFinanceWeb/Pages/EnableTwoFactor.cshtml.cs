using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using RgbFinanceWeb.Data;
using System.Text;
using System.Text.Encodings.Web;

namespace RgbFinanceWeb.Pages
{
    public class EnableTwoFactorModel : PageModel
    {
        private readonly UserManager<AppUser> _userManager;
        private readonly UrlEncoder           _urlEncoder;

        public string?  AuthenticatorUri { get; set; }
        public string?  SharedKey        { get; set; }
        public bool     IsEnabled        { get; set; }
        public string?  SuccessMessage   { get; set; }
        public string?  ErrorMessage     { get; set; }

        public EnableTwoFactorModel(UserManager<AppUser> userManager, UrlEncoder urlEncoder)
        {
            _userManager = userManager;
            _urlEncoder  = urlEncoder;
        }

        public async Task OnGetAsync()
        {
            var user = await _userManager.GetUserAsync(User);
            if (user == null) return;

            IsEnabled = await _userManager.GetTwoFactorEnabledAsync(user);
            Console.WriteLine($"[2FA DEBUG] IsEnabled: {IsEnabled}, User: {user.Email}");

            
            if (!IsEnabled)
                await LoadSharedKeyAndQrCode(user);
        }

        public async Task<IActionResult> OnPostAsync(string code)
        {
            var user = await _userManager.GetUserAsync(User);
            if (user == null) return RedirectToPage("/Login");

            var verificationCode = code.Replace(" ", "").Replace("-", "");
            var is2faTokenValid  = await _userManager.VerifyTwoFactorTokenAsync(
                user, _userManager.Options.Tokens.AuthenticatorTokenProvider, verificationCode);

            if (!is2faTokenValid)
            {
                await LoadSharedKeyAndQrCode(user);
                ErrorMessage = "Invalid verification code.";
                return Page();
            }

            await _userManager.SetTwoFactorEnabledAsync(user, true);
            SuccessMessage = "2FA has been enabled successfully.";
            IsEnabled      = true;
            return Page();
        }

        private async Task LoadSharedKeyAndQrCode(AppUser user)
        {
            var unformattedKey = await _userManager.GetAuthenticatorKeyAsync(user);
            
            if (string.IsNullOrEmpty(unformattedKey))
            {
                await _userManager.ResetAuthenticatorKeyAsync(user);
                unformattedKey = await _userManager.GetAuthenticatorKeyAsync(user);
            }

            SharedKey        = FormatKey(unformattedKey!);
            AuthenticatorUri = GenerateQrCodeUri(user.Email!, unformattedKey!);
        }
        private static string FormatKey(string unformattedKey)
        {
            var result  = new StringBuilder();
            var offset  = 0;
            while (offset + 4 < unformattedKey.Length)
            {
                result.Append(unformattedKey.AsSpan(offset, 4));
                result.Append(' ');
                offset += 4;
            }
            result.Append(unformattedKey.AsSpan(offset));
            return result.ToString().ToLowerInvariant();
        }

        private string GenerateQrCodeUri(string email, string unformattedKey) =>
            $"otpauth://totp/RgbFinance:{_urlEncoder.Encode(email)}?secret={unformattedKey}&issuer=RgbFinance&digits=6";
    }
}