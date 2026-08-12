using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text.RegularExpressions;
using System.Xml.Linq;

class InspectWorkoutHistory
{
    static readonly XNamespace Ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main";
    static readonly XNamespace RelNs = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
    static readonly XNamespace PkgRelNs = "http://schemas.openxmlformats.org/package/2006/relationships";

    static int Main(string[] args)
    {
        var path = args.Length > 0 ? args[0] : Path.Combine("master", "workout_history_master.xlsx");
        using (var fs = File.Open(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
        using (var zip = new ZipArchive(fs, ZipArchiveMode.Read))
        {
            var sheets = SheetEntries(zip);
            Console.WriteLine("sheets=" + string.Join(", ", sheets.Keys.ToArray()));
            foreach (var name in sheets.Keys)
            {
                var rows = ReadSheet(zip, sheets[name]);
                Console.WriteLine(name + ": rows=" + rows.Count);
                if (rows.Count > 0) Console.WriteLine(name + ": headers=" + string.Join("|", rows[0].Keys.Where(k => k != "_row").ToArray()));
                if (name == "Workout_History_Sessions") SummarizeSessions(rows);
                if (name == "Workout_History_Items") SummarizeItems(rows);
                if (name == "Workout_History_Summary") SummarizeSummaries(rows);
            }
        }
        return 0;
    }

    static void SummarizeSessions(List<Dictionary<string, string>> rows)
    {
        PrintCounts("session_status", rows.Select(r => Get(r, "completion_status")));
        PrintCounts("session_pain", rows.Select(r => Get(r, "pain_reported")));
        PrintCounts("recovery_flag", rows.Select(r => Get(r, "recovery_flag")));
        Console.WriteLine("sessions_unique_plans=" + rows.Select(r => Get(r, "plan_id")).Distinct().Count());
        Console.WriteLine("sessions_unique_users=" + rows.Select(r => Get(r, "user_id")).Distinct().Count());
    }

    static void SummarizeItems(List<Dictionary<string, string>> rows)
    {
        PrintCounts("item_status", rows.Select(r => Get(r, "completion_status")));
        PrintCounts("item_feedback", rows.Select(r => Get(r, "feedback_signal")));
        PrintCounts("item_pain", rows.Select(r => Get(r, "pain_during_exercise")));
    }

    static void SummarizeSummaries(List<Dictionary<string, string>> rows)
    {
        PrintCounts("summary_status", rows.Select(r => Get(r, "session_status")));
        PrintCounts("progression", rows.Select(r => Get(r, "progression_recommendation")));
    }

    static void PrintCounts(string label, IEnumerable<string> values)
    {
        var total = values.Count();
        foreach (var g in values.GroupBy(v => v).OrderByDescending(g => g.Count()))
            Console.WriteLine(label + "." + (g.Key == "" ? "<blank>" : g.Key) + "=" + g.Count() + " (" + (100.0 * g.Count() / Math.Max(1, total)).ToString("0.0", CultureInfo.InvariantCulture) + "%)");
    }

    static Dictionary<string, string> SheetEntries(ZipArchive zip)
    {
        var workbook = XDocument.Load(zip.GetEntry("xl/workbook.xml").Open());
        var rels = XDocument.Load(zip.GetEntry("xl/_rels/workbook.xml.rels").Open());
        var result = new Dictionary<string, string>();
        foreach (var sheet in workbook.Descendants(Ns + "sheet"))
        {
            var name = (string)sheet.Attribute("name");
            var rid = (string)sheet.Attribute(RelNs + "id");
            var target = (string)rels.Descendants(PkgRelNs + "Relationship").First(r => (string)r.Attribute("Id") == rid).Attribute("Target");
            target = target.TrimStart('/');
            result[name] = target.StartsWith("xl/") ? target : "xl/" + target;
        }
        return result;
    }

    static List<Dictionary<string, string>> ReadSheet(ZipArchive zip, string entryName)
    {
        var shared = Shared(zip);
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
            if (obj.Count > 1) rows.Add(obj);
        }
        return rows;
    }

    static List<string> Shared(ZipArchive zip)
    {
        var entry = zip.GetEntry("xl/sharedStrings.xml");
        if (entry == null) return new List<string>();
        var doc = XDocument.Load(entry.Open());
        return doc.Descendants(Ns + "si").Select(si => string.Concat(si.Descendants(Ns + "t").Select(t => t.Value))).ToList();
    }

    static string Text(XElement cell, List<string> shared)
    {
        var t = (string)cell.Attribute("t");
        if (t == "s")
        {
            int idx;
            return int.TryParse(cell.Value, out idx) && idx >= 0 && idx < shared.Count ? shared[idx] : "";
        }
        if (t == "inlineStr") return string.Concat(cell.Descendants(Ns + "t").Select(x => x.Value));
        return cell.Value ?? "";
    }

    static string Col(string cellRef) { return Regex.Replace(cellRef ?? "", "\\d", ""); }
    static string Get(Dictionary<string, string> r, string k) { return r.ContainsKey(k) ? (r[k] ?? "").Trim() : ""; }
}
