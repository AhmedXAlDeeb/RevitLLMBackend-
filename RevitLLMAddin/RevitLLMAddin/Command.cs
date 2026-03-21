using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using Autodesk.Revit.UI;
using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;

namespace RevitLLMAddin
{
    [Transaction(TransactionMode.Manual)]
    public class Command : IExternalCommand
    {
        public Result Execute(
            ExternalCommandData commandData,
            ref string message,
            ElementSet elements)
        {
            try
            {
                UIDocument uidoc = commandData.Application.ActiveUIDocument;
                Document doc = uidoc.Document;

                var rooms = GetRooms(doc);
                var doors = GetDoors(doc);
                var stairs = GetStairs(doc);

                var modelData = new
                {
                    rooms = rooms,
                    doors = doors,
                    stairs = stairs
                };

                SendToBackend(modelData);

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                TaskDialog.Show("Error", ex.ToString());
                return Result.Failed;
            }
        }

        // ---------------- ROOMS ----------------

        private List<object> GetRooms(Document doc)
        {
            List<object> roomsData = new List<object>();

            FilteredElementCollector collector =
                new FilteredElementCollector(doc)
                .OfCategory(BuiltInCategory.OST_Rooms)
                .WhereElementIsNotElementType();

            foreach (Element room in collector)
            {
                Parameter areaParam = room.get_Parameter(BuiltInParameter.ROOM_AREA);
                if (areaParam == null) continue;

                double areaInternal = areaParam.AsDouble();

                double areaMeters =
                    UnitUtils.ConvertFromInternalUnits(
                        areaInternal,
                        UnitTypeId.SquareMeters
                    );

                roomsData.Add(new
                {
                    name = room.Name,
                    area = Math.Round(areaMeters, 2)
                });
            }

            return roomsData;
        }

        // ---------------- DOORS ----------------

        private List<object> GetDoors(Document doc)
        {
            List<object> doorsData = new List<object>();

            FilteredElementCollector collector =
                new FilteredElementCollector(doc)
                .OfCategory(BuiltInCategory.OST_Doors)
                .WhereElementIsNotElementType();

            foreach (FamilyInstance door in collector)
            {
                Parameter widthParam = door.Symbol.get_Parameter(BuiltInParameter.DOOR_WIDTH);
                Parameter heightParam = door.Symbol.get_Parameter(BuiltInParameter.DOOR_HEIGHT);

                if (widthParam == null || heightParam == null) continue;

                double width =
                    UnitUtils.ConvertFromInternalUnits(
                        widthParam.AsDouble(),
                        UnitTypeId.Millimeters
                    );

                double height =
                    UnitUtils.ConvertFromInternalUnits(
                        heightParam.AsDouble(),
                        UnitTypeId.Millimeters
                    );

                doorsData.Add(new
                {
                    width = Math.Round(width),
                    height = Math.Round(height)
                });
            }

            return doorsData;
        }

        // ---------------- STAIRS ----------------

        private List<object> GetStairs(Document doc)
        {
            List<object> stairsData = new List<object>();

            FilteredElementCollector collector =
                new FilteredElementCollector(doc)
                .OfClass(typeof(Stairs));

            foreach (Stairs stair in collector)
            {
                Parameter widthParam =
                    stair.get_Parameter(BuiltInParameter.STAIRS_RUN_ACTUAL_RUN_WIDTH);

                double width = 0;

                if (widthParam != null)
                {
                    width =
                        UnitUtils.ConvertFromInternalUnits(
                            widthParam.AsDouble(),
                            UnitTypeId.Millimeters
                        );
                }

                stairsData.Add(new
                {
                    width = Math.Round(width)
                });
            }

            return stairsData;
        }

        // ---------------- BACKEND ----------------

        private void SendToBackend(object data)
        {
            using (HttpClient client = new HttpClient())
            {
                client.Timeout = TimeSpan.FromSeconds(5);

                var json = JsonConvert.SerializeObject(data);

                var content = new StringContent(
                    json,
                    Encoding.UTF8,
                    "application/json"
                );

                var response = client.PostAsync(
                    "http://127.0.0.1:8000/modeldata",
                    content
                ).Result;

                var result = response.Content.ReadAsStringAsync().Result;

                TaskDialog.Show("Backend Reply", result);
            }
        }
    }
}