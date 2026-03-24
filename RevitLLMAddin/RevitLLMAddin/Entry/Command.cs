using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using Autodesk.Revit.UI;
using Newtonsoft.Json;
using RevitLLMAddin.Clients;
using RevitLLMAddin.Models;
using RevitLLMAddin.Services;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Text;


namespace RevitLLMAddin
{
    [Transaction(TransactionMode.Manual)]
    public class CheckComplianceCommand : IExternalCommand
    {
        public Result Execute(
            ExternalCommandData commandData,
            ref string message,
            ElementSet elements)
        {
            try
            {
                var uidoc = commandData.Application.ActiveUIDocument;
                Document doc = uidoc.Document;

                // Services
                var roomService = new RoomService();
                var apiClient = new ApiClient();

                // Step 1: Get rooms
                var rooms = roomService.GetRooms(doc);

                if (rooms == null || rooms.Count == 0)
                {
                    TaskDialog.Show("Warning", "No valid rooms found.");
                    return Result.Cancelled;
                }

                // Step 2: Send to API
                var results = apiClient.CheckCompliance(rooms);

                if (results == null || results.Count == 0)
                {
                    TaskDialog.Show("Warning", "No response from server.");
                    return Result.Failed;
                }


                // =====================================================
                // 🔥 ADD YOUR HIGHLIGHTING CODE HERE
                // =====================================================

                // Step 3: Get failed IDs
                var failedIds = results
                    .Where(r => r.Status == "fail")
                    .Select(r => r.Id)
                    .ToList();

                if (failedIds.Count == 0)
                {
                    TaskDialog.Show("Result", "All rooms are compliant ✅");
                    return Result.Succeeded;
                }

                // Step 4: Convert to ElementId
                var elementIds = failedIds
                    .Select(id =>
                    {
                        ElementId elementId = new ElementId((long)id);
                        return elementId;
                    })
                    .ToList();

                // Step 5: Select in Revit
                uidoc.Selection.SetElementIds(elementIds);

                var fillPattern = new FilteredElementCollector(doc)
                   .OfClass(typeof(FillPatternElement))
                   .Cast<FillPatternElement>()
                   .FirstOrDefault(fp => fp.GetFillPattern().IsSolidFill);

                // Step 6: Create override settings
                OverrideGraphicSettings ogs = new OverrideGraphicSettings();
                Color red = new Color(255, 0, 0);

                ogs.SetProjectionLineColor(red);
                ogs.SetSurfaceForegroundPatternColor(red);
                ogs.SetSurfaceForegroundPatternId(fillPattern.Id);

                // Step 7: Apply highlight (Transaction REQUIRED)
                using (Transaction tx = new Transaction(doc, "Highlight Failed Rooms"))
                {
                    tx.Start();

                    foreach (var id in elementIds)
                    {
                        doc.ActiveView.SetElementOverrides(id, ogs);
                    }

                    tx.Commit();
                }

                // =====================================================
                // 🔚 END OF HIGHLIGHTING
                // =====================================================



                // Step 8: Show result

                string output = string.Join("\n",
                                   results.Select(r =>
                                       $"Room: {r.Id} >> {r.Status}" +
                                       (string.IsNullOrEmpty(r.Message) ? "" : $" ({r.Message})")
                                   ));

                TaskDialog.Show("Compliance Results", output);

                return Result.Succeeded;
            }

            catch (Exception ex)
            {
                // Catch ANY unexpected error
                TaskDialog.Show("Error", ex.Message);

                return Result.Failed;
            }
        }


}
}