using Newtonsoft.Json;
using RevitLLMAddin.Models;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;

namespace RevitLLMAddin.Clients
{
    public class ApiClient
    {
        private readonly string _url = "http://127.0.0.1:8000/check-compliance";

        public List<ComplianceResult> CheckCompliance(List<RoomModel> rooms)
        {
            var json = JsonConvert.SerializeObject(rooms);

            using (var client = new HttpClient())
            {
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                var response = client.PostAsync(_url, content).Result;

                if (!response.IsSuccessStatusCode)
                {
                    throw new Exception("API call failed: " + response.StatusCode);
                }


                var result = response.Content.ReadAsStringAsync().Result;

                return JsonConvert.DeserializeObject<List<ComplianceResult>>(result);
            }
        }
    }
}
