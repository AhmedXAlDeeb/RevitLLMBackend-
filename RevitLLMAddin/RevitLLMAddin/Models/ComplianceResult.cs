using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace RevitLLMAddin.Models
{
    public class ComplianceResult
    {
        public int Id { get; set; }
        public string Status { get; set; }
        public string Message { get; set; }
    }
}
