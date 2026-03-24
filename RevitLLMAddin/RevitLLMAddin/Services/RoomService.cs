using Autodesk.Revit.DB;
using RevitLLMAddin.Models;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace RevitLLMAddin.Services
{
    public class RoomService
    {
        public List<RoomModel> GetRooms(Document doc)
        {
            var rooms = new FilteredElementCollector(doc)
                .OfCategory(BuiltInCategory.OST_Rooms)
                .WhereElementIsNotElementType();

            var result = new List<RoomModel>();

            foreach (var room in rooms)
            {
                double area = UnitUtils.ConvertFromInternalUnits(
                    room.get_Parameter(BuiltInParameter.ROOM_AREA).AsDouble(),
                    UnitTypeId.SquareMeters);

                if (area <= 0) continue;

                string name = room.Name ?? "Unknown";

                result.Add(new RoomModel
                {
                    Id = (int)room.Id.Value,
                    Name = room.Name,
                    Area = area
                });
            }

            return result;
        }
    }
}
