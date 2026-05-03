using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using RgbFinanceWeb.Data;
using RgbFinanceWeb.Endpoints;
using DotNetEnv;


var builder = WebApplication.CreateBuilder(args);
Env.Load(Path.Combine(Directory.GetCurrentDirectory(), "..", ".env"));

// Environment variable'ları configuration'a ekle
builder.Configuration["ConnectionStrings:DefaultConnection"] = 
    Environment.GetEnvironmentVariable("SQLSERVER_CONNECTION") 
    ?? builder.Configuration.GetConnectionString("DefaultConnection");

builder.Configuration["Finnhub:ApiKey"] = 
    Environment.GetEnvironmentVariable("FINNHUB_API_KEY") 
    ?? builder.Configuration["Finnhub:ApiKey"];

builder.Configuration["AdminSettings:Email"] = 
    Environment.GetEnvironmentVariable("ADMIN_EMAIL") 
    ?? builder.Configuration["AdminSettings:Email"];

var apiBaseUrl = builder.Configuration["ApiSettings:BaseUrl"] ?? "http://localhost:8000/";

builder.Services.AddHttpClient("FinanceApi", client =>
{
    client.BaseAddress = new Uri(apiBaseUrl);
    client.Timeout     = TimeSpan.FromSeconds(300);
});

builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection")));

builder.Services.AddIdentity<AppUser, IdentityRole>(options =>
{
    options.SignIn.RequireConfirmedAccount   = false;
    options.Password.RequireDigit           = true;
    options.Password.RequiredLength         = 8;
    options.Password.RequireNonAlphanumeric = false;
})
.AddEntityFrameworkStores<AppDbContext>()
.AddDefaultTokenProviders();

builder.Services.ConfigureApplicationCookie(options =>
{
    options.LoginPath        = "/Landing";
    options.LogoutPath       = "/Logout";
    options.AccessDeniedPath = "/AccessDenied";
});

builder.Services.AddRazorPages();

var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseRouting();
app.UseAuthentication();
app.UseAuthorization();
app.MapStaticAssets();
app.MapRazorPages().WithStaticAssets();

// ── Proxy Endpoints ───────────────────────────────────────────────────

app.MapProxyEndpoints();

// ── Prediction Endpoints ───────────────────────────────────────────────────

app.MapPredictionEndpoints();


// ── Admin role setup ──────────────────────────────────────────

using (var scope = app.Services.CreateScope())
{
    var roleManager = scope.ServiceProvider.GetRequiredService<RoleManager<IdentityRole>>();
    var userManager = scope.ServiceProvider.GetRequiredService<UserManager<AppUser>>();

    if (!await roleManager.RoleExistsAsync("Admin"))
        await roleManager.CreateAsync(new IdentityRole("Admin"));

    var adminEmail = app.Configuration["AdminSettings:Email"];
    if (adminEmail != null)
    {
        var adminUser = await userManager.FindByEmailAsync(adminEmail);
        if (adminUser != null && !await userManager.IsInRoleAsync(adminUser, "Admin"))
            await userManager.AddToRoleAsync(adminUser, "Admin");
    }
}

app.Run();
