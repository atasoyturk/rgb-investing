using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;

namespace RgbFinanceWeb.Data
{
    public class AppUser : IdentityUser
    {
    }

    public class UserTicker
    {
        public int    Id     { get; set; }
        public string UserId { get; set; } = string.Empty;
        public string Symbol { get; set; } = string.Empty;
        public string Market { get; set; } = "SP500";

    }

    public class Prediction
    {
        public int      Id            { get; set; }
        public string   Ticker        { get; set; } = string.Empty;
        public string   Market        { get; set; } = string.Empty;
        public string   Signal        { get; set; } = string.Empty;
        public float    Confidence    { get; set; }
        public float    PriceAtSignal { get; set; }
        public DateTime PredictedDate { get; set; }
        public DateTime TargetDate    { get; set; }
        public bool?    ActualOutcome { get; set; }  // null = henüz bilinmiyor
        public float?   ActualPrice   { get; set; }
        public float    Threshold     { get; set; } = 0.03f; // default fallback
    }
    
    public class AppDbContext : IdentityDbContext<AppUser>
    {
        public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }
        public DbSet<UserTicker> UserTickers { get; set; }
        public DbSet<Prediction> Predictions { get; set; }

    }
}