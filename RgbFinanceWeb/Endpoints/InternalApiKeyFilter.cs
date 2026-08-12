namespace RgbFinanceWeb.Endpoints
{
    public class InternalApiKeyFilter : IEndpointFilter
    {
        private readonly IConfiguration _configuration;

        public InternalApiKeyFilter(IConfiguration configuration)
        {
            _configuration = configuration;
        }

        public async ValueTask<object?> InvokeAsync(EndpointFilterInvocationContext context, EndpointFilterDelegate next)
        {
            var accepted = new[]
            {
                _configuration["InternalApi:AirflowKey"],
                _configuration["InternalApi:ApiKey"]
            }
            .Where(k => !string.IsNullOrEmpty(k))
            .ToHashSet();

            if (accepted.Count == 0)
                return await next(context); // Henüz key konfigüre edilmemiş

            var provided = context.HttpContext.Request.Headers["X-Internal-Api-Key"].ToString();
            if (string.IsNullOrEmpty(provided) || !accepted.Contains(provided))
                return Results.Unauthorized();

            return await next(context);
        }
    }
}