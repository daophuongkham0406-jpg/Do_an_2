using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text.RegularExpressions;
using System.Xml.Linq;

class FixUserValidationFast
{
    static readonly XNamespace Ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main";
    static readonly XNamespace RelNs = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
    static readonly XNamespace PkgRelNs = "http://schemas.openxmlformats.org/package/2006/relationships";

    class Up
    {
        public string Value;
        public bool Number;
        public Up(string value, bool number) { Value = value; Number = number; }
    }

    static int Main()
    {
        var root = Directory.GetCurrentDirectory();
        var master = Path.Combine(root, "master");
        var backup = Path.Combine(master, "backups");
        Directory.CreateDirectory(backup);

        var userPath = Path.Combine(master, "user_master.xlsx");
        var stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
        File.Copy(userPath, Path.Combine(backup, "user_master_before_user_validation_fix_" + stamp + ".xlsx"), true);

        var users = ReadSheet(userPath, "User_Profile");
        var references = ReadSheet(userPath, "Reference_Lists");
        var mappings = ReadSheet(userPath, "Goal_Mapping");
        var updates = new Dictionary<int, Dictionary<string, Up>>();

        var goalMapping = mappings
            .Where(r => Get(r, "user_goal") != "" && Get(r, "exercise_goal_tags_json") != "")
            .GroupBy(r => Get(r, "user_goal"))
            .ToDictionary(g => g.Key, g => Json(ParseJsonArray(Get(g.First(), "exercise_goal_tags_json"))));

        var canonicalEquipment = new HashSet<string>(
            references.Select(r => Get(r, "canonical_equipment")).Where(v => v != ""),
            StringComparer.OrdinalIgnoreCase);
        var canonicalGoals = new HashSet<string>(
            references.Select(r => Get(r, "canonical_recommended_goals")).Where(v => v != ""),
            StringComparer.OrdinalIgnoreCase);

        foreach (var user in users)
        {
            var primaryGoal = Get(user, "primary_goal");
            if (goalMapping.ContainsKey(primaryGoal))
                SetCellValue(user, "goal_filter_tags", goalMapping[primaryGoal], false, updates);

            var equipment = ParseJsonArray(Get(user, "available_equipment"))
                .Select(NormalizeEquipment)
                .Where(v => v != "")
                .Where(v => canonicalEquipment.Contains(v))
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToList();

            if (equipment.Count == 0 && canonicalEquipment.Contains("Bodyweight"))
                equipment.Add("Bodyweight");

            SetCellValue(user, "available_equipment", Json(equipment), false, updates);
        }

        UpdateSheet(userPath, "User_Profile", updates);

        var audit = Audit(users, goalMapping, canonicalGoals, canonicalEquipment);
        Console.WriteLine("User validation cleanup complete");
        Console.WriteLine("user_rows_updated=" + updates.Count);
        Console.WriteLine("post_audit_total=" + audit.Values.Sum());
        foreach (var kv in audit.OrderBy(kv => kv.Key))
            Console.WriteLine("post_audit_" + kv.Key + "=" + kv.Value);
        Console.WriteLine("backup_stamp=" + stamp);
        return audit.Values.Sum() == 0 ? 0 : 1;
    }

    static Dictionary<string, int> Audit(List<Dictionary<string, string>> users, Dictionary<string, string> goalMapping, HashSet<string> canonicalGoals, HashSet<string> canonicalEquipment)
    {
        var counts = new Dictionary<string, int>();
        Action<string> add = code => { if (!counts.ContainsKey(code)) counts[code] = 0; counts[code]++; };
        foreach (var user in users)
        {
            var primaryGoal = Get(user, "primary_goal");
            if (goalMapping.ContainsKey(primaryGoal))
            {
                var actual = new HashSet<string>(ParseJsonArray(Get(user, "goal_filter_tags")));
                var expected = new HashSet<string>(ParseJsonArray(goalMapping[primaryGoal]));
                if (!actual.SetEquals(expected)) add("ERROR_GOAL_MAPPING_MISMATCH");
            }
            foreach (var tag in ParseJsonArray(Get(user, "goal_filter_tags")))
                if (!canonicalGoals.Contains(tag))
                    add("ERROR_INVALID_GOAL_TAG");
            foreach (var tag in ParseJsonArray(Get(user, "available_equipment")))
                if (!canonicalEquipment.Contains(tag))
                    add("ERROR_INVALID_EQUIPMENT");
        }
        return counts;
    }

    static string NormalizeEquipment(string value)
    {
        var text = (value ?? "").Trim();
        if (text.Equals("Weight Plate Or Block", StringComparison.OrdinalIgnoreCase)) return "Weight Plate";
        if (text.Equals("Weight Plates Or Block", StringComparison.OrdinalIgnoreCase)) return "Weight Plate";
        if (text.Equals("Bench Or Box", StringComparison.OrdinalIgnoreCase)) return "Bench";
        if (text.Equals("Partner Or Anchor Point", StringComparison.OrdinalIgnoreCase)) return "Anchor Point";
        if (text.Equals("Straight Bar Or Rope", StringComparison.OrdinalIgnoreCase)) return "Straight Bar or Rope";
        if (text.Equals("Flat Bench Or Mat", StringComparison.OrdinalIgnoreCase)) return "Flat Bench or Mat";
        if (text.Equals("Plyo Box Or Bench", StringComparison.OrdinalIgnoreCase)) return "Plyo Box or Bench";
        return text;
    }

    static List<Dictionary<string, string>> ReadSheet(string path, string sheetName)
    {
        using (var fs = File.Open(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
        using (var zip = new ZipArchive(fs, ZipArchiveMode.Read))
        {
            var shared = Shared(zip);
            var entryName = SheetEntry(zip, sheetName);
            XDocument doc;
            using (var s = zip.GetEntry(entryName).Open()) doc = XDocument.Load(s);
            var headers = new Dictionary<string, string>();
            var rows = new List<Dictionary<string, string>>();
            foreach (var row in doc.Descendants(Ns + "row"))
            {
                var rowNum = (int)row.Attribute("r");
                if (rowNum == 1)
                {
                    foreach (var cell in row.Elements(Ns + "c")) headers[Col((string)cell.Attribute("r"))] = Text(cell, shared);
                    continue;
                }
                var obj = new Dictionary<string, string> { { "_row", rowNum.ToString(CultureInfo.InvariantCulture) } };
                foreach (var cell in row.Elements(Ns + "c"))
                {
                    var col = Col((string)cell.Attribute("r"));
                    if (headers.ContainsKey(col)) obj[headers[col]] = Text(cell, shared);
                }
                rows.Add(obj);
            }
            return rows;
        }
    }

    static void UpdateSheet(string path, string sheetName, Dictionary<int, Dictionary<string, Up>> updates)
    {
        if (updates.Count == 0) return;
        using (var fs = File.Open(path, FileMode.Open, FileAccess.ReadWrite, FileShare.None))
        using (var zip = new ZipArchive(fs, ZipArchiveMode.Update))
        {
            var shared = Shared(zip);
            var entryName = SheetEntry(zip, sheetName);
            var entry = zip.GetEntry(entryName);
            XDocument doc;
            using (var s = entry.Open()) doc = XDocument.Load(s);
            var headers = new Dictionary<string, string>();
            var headerRow = doc.Descendants(Ns + "row").First(r => (int)r.Attribute("r") == 1);
            foreach (var cell in headerRow.Elements(Ns + "c")) headers[Text(cell, shared)] = Col((string)cell.Attribute("r"));
            var rowsByNumber = doc.Descendants(Ns + "row").ToDictionary(r => (int)r.Attribute("r"), r => r);
            var cellsByRef = doc.Descendants(Ns + "c").Where(c => c.Attribute("r") != null).ToDictionary(c => (string)c.Attribute("r"), c => c);
            foreach (var rowUpdate in updates)
                foreach (var colUpdate in rowUpdate.Value)
                    if (headers.ContainsKey(colUpdate.Key)) SetCell(rowsByNumber, cellsByRef, rowUpdate.Key, headers[colUpdate.Key], colUpdate.Value.Value, colUpdate.Value.Number);
            entry.Delete();
            var newEntry = zip.CreateEntry(entryName);
            using (var s = newEntry.Open()) doc.Save(s);
        }
    }

    static void SetCell(Dictionary<int, XElement> rowsByNumber, Dictionary<string, XElement> cellsByRef, int rowNum, string col, string value, bool number)
    {
        var row = rowsByNumber[rowNum];
        var cellRef = col + rowNum.ToString(CultureInfo.InvariantCulture);
        XElement cell;
        cellsByRef.TryGetValue(cellRef, out cell);
        if (cell == null)
        {
            cell = new XElement(Ns + "c", new XAttribute("r", cellRef));
            row.Add(cell);
            cellsByRef[cellRef] = cell;
        }
        cell.RemoveNodes();
        cell.Attributes("t").Remove();
        if (number) cell.Add(new XElement(Ns + "v", value));
        else
        {
            cell.SetAttributeValue("t", "inlineStr");
            cell.Add(new XElement(Ns + "is", new XElement(Ns + "t", value)));
        }
    }

    static List<string> Shared(ZipArchive zip)
    {
        var entry = zip.GetEntry("xl/sharedStrings.xml");
        if (entry == null) return new List<string>();
        XDocument doc;
        using (var s = entry.Open()) doc = XDocument.Load(s);
        return doc.Descendants(Ns + "si").Select(si => string.Concat(si.Descendants(Ns + "t").Select(t => t.Value))).ToList();
    }

    static string SheetEntry(ZipArchive zip, string sheetName)
    {
        XDocument workbook, rels;
        using (var s = zip.GetEntry("xl/workbook.xml").Open()) workbook = XDocument.Load(s);
        using (var s = zip.GetEntry("xl/_rels/workbook.xml.rels").Open()) rels = XDocument.Load(s);
        var sheet = workbook.Descendants(Ns + "sheet").First(s => (string)s.Attribute("name") == sheetName);
        var rid = (string)sheet.Attribute(RelNs + "id");
        var target = (string)rels.Descendants(PkgRelNs + "Relationship").First(r => (string)r.Attribute("Id") == rid).Attribute("Target");
        target = target.TrimStart('/');
        return target.StartsWith("xl/") ? target : "xl/" + target;
    }

    static void SetCellValue(Dictionary<string, string> row, string col, string val, bool num, Dictionary<int, Dictionary<string, Up>> updates)
    {
        var rowNum = I(Get(row, "_row"));
        if (!updates.ContainsKey(rowNum)) updates[rowNum] = new Dictionary<string, Up>();
        updates[rowNum][col] = new Up(val, num);
        row[col] = val;
    }

    static string Text(XElement cell, List<string> shared)
    {
        var t = (string)cell.Attribute("t");
        if (t == "s")
        {
            var idx = I(cell.Value);
            return idx >= 0 && idx < shared.Count ? shared[idx] : "";
        }
        if (t == "inlineStr") return string.Concat(cell.Descendants(Ns + "t").Select(x => x.Value));
        return cell.Value ?? "";
    }

    static List<string> ParseJsonArray(string json)
    {
        return Regex.Matches(json ?? "", "\"((?:\\\\.|[^\"])*)\"")
            .Cast<Match>()
            .Select(m => m.Groups[1].Value.Replace("\\\"", "\"").Replace("\\\\", "\\").Trim())
            .Where(v => v != "")
            .ToList();
    }

    static string Json(IEnumerable<string> values)
    {
        return "[" + string.Join(",", values.Where(v => !string.IsNullOrWhiteSpace(v)).Select(v => "\"" + v.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"").ToArray()) + "]";
    }

    static string Col(string cellRef) { return Regex.Replace(cellRef ?? "", "\\d", ""); }
    static string Get(Dictionary<string, string> r, string k) { return r.ContainsKey(k) ? (r[k] ?? "").Trim() : ""; }
    static int I(string s) { int v; return int.TryParse((s ?? "").Split('.')[0], NumberStyles.Any, CultureInfo.InvariantCulture, out v) ? v : 0; }
}
