namespace RgbFinanceWeb.Models
{
    public class SignalModel
    {
        public string  Ticker        { get; set; } = string.Empty;
        public string Currency { get; set; } = "$";
        public string  Signal        { get; set; } = string.Empty;
        public double  Confidence    { get; set; }
        public double? LastPrice     { get; set; }
        public int     FutureDays    { get; set; }
        public bool    InTrainingSet { get; set; }
    }

    public class SignalsTableModel
    {
        public List<SignalModel> Signals       { get; set; } = new();
        public double?           ModelF1       { get; set; }
        public double?           ModelAccuracy { get; set; }
    }

    public class HealthModel
    {
        public string        Status      { get; set; } = string.Empty;
        public bool          ModelLoaded { get; set; }
        public List<string>  Tickers     { get; set; } = new();
        public int           WindowSize  { get; set; }
        public int           FutureDays  { get; set; }
        public double?       F1Macro     { get; set; }
    }
}
