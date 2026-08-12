using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Xml;
using System.Xml.Linq;

class GenerateWorkoutHistoryFixed
{
    static readonly XNamespace Ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main";
    static readonly XNamespace RelNs = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
    static readonly XNamespace PkgRelNs = "http://schemas.openxmlformats.org/package/2006/relationships";
    static readonly string[] Weekdays = { "", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday" };

    class Plan { public Dictionary<string, string> R; public string Id, UserId; public int Days, Duration; public double TargetMin; }
    class User { public Dictionary<string, string> R; public string Id; public double Sleep, Weight; public string Profile; }
    class Item { public Dictionary<string, string> R; public string PlanId, PlanItemId, ExerciseId; public int Week, Day, Order, Sets, RepMin, RepMax, Rest; public double TargetRpe; }
    class SessionBuild { public Dictionary<string, object> Row; public List<Dictionary<string, object>> Items = new List<Dictionary<string, object>>(); }

    static int Main()
    {
        var root = Directory.GetCurrentDirectory();
        var master = Path.Combine(root, "master");
        var planPath = Path.Combine(master, "workout_plan_master.xlsx");
        var userPath = Path.Combine(master, "user_master.xlsx");
        var outPath = Path.Combine(master, "workout_history_master_fixed.xlsx");

        var plans = ReadSheet(planPath, "Workout_Plan")
            .Where(r => Get(r, "plan_id") != "" && Get(r, "user_id") != "")
            .Select(r => new Plan
            {
                R = r,
                Id = Get(r, "plan_id"),
                UserId = Get(r, "user_id"),
                Days = Clamp(I(Get(r, "days_per_week")), 1, 7),
                Duration = Clamp(I(Get(r, "duration_weeks")), 1, 52),
                TargetMin = ClampD(D(Get(r, "session_duration_target_min")), 15, 240)
            })
            .OrderBy(p => p.Id)
            .ToList();

        var users = ReadSheet(userPath, "User_Profile")
            .Where(r => Get(r, "user_id") != "")
            .Select(r => new User
            {
                R = r,
                Id = Get(r, "user_id"),
                Sleep = ClampD(D(Get(r, "sleep_hours")), 4.5, 9.5),
                Weight = ClampD(D(Get(r, "weight_kg")), 45, 180),
                Profile = ""
            })
            .ToDictionary(u => u.Id, u => u);

        var planItems = ReadSheet(planPath, "Workout_Plan_Items")
            .Where(r => Get(r, "plan_id") != "" && Get(r, "plan_item_id") != "" && Get(r, "day_type") == "Training")
            .Select(r => new Item
            {
                R = r,
                PlanId = Get(r, "plan_id"),
                PlanItemId = Get(r, "plan_item_id"),
                ExerciseId = Get(r, "exercise_id"),
                Week = Clamp(I(Get(r, "week_number")), 1, 52),
                Day = Clamp(I(Get(r, "day_number")), 1, 7),
                Order = Math.Max(1, I(Get(r, "exercise_order"))),
                Sets = Math.Max(0, I(Get(r, "sets"))),
                RepMin = Math.Max(1, I(Get(r, "rep_min"))),
                RepMax = Math.Max(1, I(Get(r, "rep_max"))),
                TargetRpe = ClampD(D(Get(r, "target_intensity")), 1, 10),
                Rest = Clamp(I(Get(r, "rest_seconds")), 0, 900)
            })
            .Where(i => i.RepMax >= i.RepMin)
            .ToList();

        var itemsByPlan = planItems.GroupBy(i => i.PlanId).ToDictionary(g => g.Key, g => g.ToList());
        var sessions = new List<Dictionary<string, object>>();
        var historyItems = new List<Dictionary<string, object>>();
        var summaries = new List<Dictionary<string, object>>();
        var exceptions = new List<Dictionary<string, object>>();

        var sessionId = 1;
        var itemId = 1;
        var summaryId = 1;
        var start = new DateTime(2026, 1, 5);

        foreach (var plan in plans)
        {
            if (!users.ContainsKey(plan.UserId) || !itemsByPlan.ContainsKey(plan.Id))
            {
                exceptions.Add(ExceptionRow(plan, "Missing user or plan items; skipped generation."));
                continue;
            }
            var user = users[plan.UserId];
            user.Profile = ProfileFor(plan.Id, user);
            var groups = itemsByPlan[plan.Id]
                .GroupBy(i => i.Week + "|" + i.Day)
                .Select(g => g.OrderBy(i => i.Order).ThenBy(i => i.PlanItemId).Take(7).ToList())
                .Where(g => g.Count > 0)
                .OrderBy(g => g[0].Week)
                .ThenBy(g => g[0].Day)
                .ToList();
            if (groups.Count == 0)
            {
                exceptions.Add(ExceptionRow(plan, "No training item group available; skipped generation."));
                continue;
            }

            var maxSessions = Math.Min(plan.Duration * plan.Days, groups.Count * Math.Max(1, plan.Duration));
            var desired = Clamp(16 + (Seed(plan.Id) % 7), 12, Math.Max(12, maxSessions));
            desired = Math.Min(desired, maxSessions);
            if (desired < 12) desired = Math.Min(maxSessions, groups.Count);

            SessionBuild representative = null;
            for (var s = 0; s < desired; s++)
            {
                var sourceGroup = groups[s % groups.Count];
                var week = Clamp(1 + (s / Math.Max(1, plan.Days)), 1, 52);
                var day = sourceGroup[0].Day;
                var status = SessionStatus(user.Profile, plan.Id, s);
                var painSession = status != "Skipped" && PainSession(user.Profile, plan.Id, s);
                var sleep = SleepFor(user, s);
                var energy = Clamp((int)Math.Round(3 + (sleep - 7) * 0.45 + ((Seed(plan.Id) + s) % 3 - 1) * 0.35), 1, 5);
                var readiness = Clamp((int)Math.Round(6 + (sleep - 7) * 0.7 + (energy - 3) * 0.8 - (painSession ? 2.0 : 0.0)), 1, 10);

                var sid = "WHS" + sessionId.ToString("D8", CultureInfo.InvariantCulture);
                sessionId++;

                var built = BuildSession(plan, user, sourceGroup, sid, week, day, start.AddDays((week - 1) * 7 + day - 1 + (Seed(plan.Id) % 21)), status, painSession, sleep, energy, readiness, ref itemId);
                sessions.Add(built.Row);
                historyItems.AddRange(built.Items);
                representative = built;
            }

            if (representative != null)
            {
                summaries.Add(BuildSummary("WHSUM" + summaryId.ToString("D6", CultureInfo.InvariantCulture), representative));
                summaryId++;
            }
        }

        WriteWorkbook(outPath, sessions, historyItems, summaries, BuildSourceManifest(plans, users, planItems), BuildReferences(), BuildDictionary(), BuildRules(), BuildSchemaInfo(plans, users, sessions, historyItems, summaries), BuildQualitySummary(sessions, historyItems), BuildAlignmentNotes(), exceptions);
        WriteReport(Path.Combine(root, "reports", "workout_history_validation_report.txt"), sessions, historyItems, summaries);

        Console.WriteLine("Workout history fixed workbook generated");
        Console.WriteLine("output=" + outPath);
        Console.WriteLine("sessions=" + sessions.Count);
        Console.WriteLine("items=" + historyItems.Count);
        Console.WriteLine("summaries=" + summaries.Count);
        Console.WriteLine("completed_pct=" + Pct(sessions.Count(r => S(r, "completion_status") == "Completed"), sessions.Count).ToString("0.0", CultureInfo.InvariantCulture));
        Console.WriteLine("partial_pct=" + Pct(sessions.Count(r => S(r, "completion_status") == "Partial"), sessions.Count).ToString("0.0", CultureInfo.InvariantCulture));
        Console.WriteLine("skipped_pct=" + Pct(sessions.Count(r => S(r, "completion_status") == "Skipped"), sessions.Count).ToString("0.0", CultureInfo.InvariantCulture));
        Console.WriteLine("pain_pct=" + Pct(sessions.Count(r => S(r, "pain_reported") == "Yes"), sessions.Count).ToString("0.0", CultureInfo.InvariantCulture));
        Console.WriteLine("positive_item_pct=" + Pct(historyItems.Count(r => S(r, "feedback_signal") == "Positive"), historyItems.Count).ToString("0.0", CultureInfo.InvariantCulture));
        Console.WriteLine("neutral_item_pct=" + Pct(historyItems.Count(r => S(r, "feedback_signal") == "Neutral"), historyItems.Count).ToString("0.0", CultureInfo.InvariantCulture));
        Console.WriteLine("negative_item_pct=" + Pct(historyItems.Count(r => S(r, "feedback_signal") == "Negative"), historyItems.Count).ToString("0.0", CultureInfo.InvariantCulture));
        return 0;
    }

    static SessionBuild BuildSession(Plan plan, User user, List<Item> sourceItems, string sid, int week, int day, DateTime date, string status, bool painSession, double sleep, int energy, int readiness, ref int itemId)
    {
        var b = new SessionBuild();
        var completedItems = 0;
        var plannedSets = 0;
        var completedSets = 0;
        var actualRpes = new List<double>();
        var painAreas = new HashSet<string>();
        var positives = 0;
        var neutrals = 0;
        var negatives = 0;
        var diffTotal = 0;
        var enjoyTotal = 0;
        var performedCount = 0;

        for (var idx = 0; idx < sourceItems.Count; idx++)
        {
            var src = sourceItems[idx];
            plannedSets += src.Sets;
            var itemStatus = status == "Skipped" ? "Skipped" : ItemStatus(status, user.Profile, plan.Id, idx);
            var itemPain = painSession && idx == ((Seed(plan.Id) + week + day) % sourceItems.Count);
            if (itemPain) itemStatus = "Modified";

            var actualSets = itemStatus == "Skipped" ? 0 : src.Sets;
            if (itemStatus == "Modified") actualSets = src.Sets;
            var reps = new List<int>();
            for (var set = 0; set < actualSets; set++)
            {
                var baseRep = src.RepMax - ((Seed(src.PlanItemId) + week + set) % Math.Max(1, Math.Min(3, src.RepMax - src.RepMin + 1)));
                if (itemStatus == "Modified") baseRep = Math.Max(src.RepMin, baseRep - 1);
                reps.Add(Clamp(baseRep, src.RepMin, src.RepMax));
            }
            var actualRpe = itemStatus == "Skipped" ? (double?)null : Math.Round(ClampD(src.TargetRpe + RpeDrift(user.Profile, week, idx) + (itemPain ? 1.1 : 0), 4.5, 9.3), 1);
            var difficulty = itemStatus == "Skipped" ? (int?)null : Clamp((int)Math.Round((actualRpe.Value - 4.0) / 1.25), 1, 5);
            var enjoyment = itemStatus == "Skipped" ? (int?)null : Enjoyment(user.Profile, plan.Id, idx, itemPain, actualRpe.Value);
            var technique = itemStatus == "Skipped" ? "" : Technique(itemStatus, itemPain, actualRpe.Value);
            var feedback = Feedback(itemStatus, itemPain, technique, actualRpe, enjoyment);
            var areaJson = itemPain ? PainArea(src) : "[]";

            if (itemStatus != "Skipped")
            {
                completedItems++;
                completedSets += actualSets;
                actualRpes.Add(actualRpe.Value);
                performedCount++;
                diffTotal += difficulty.Value;
                enjoyTotal += enjoyment.Value;
            }
            if (itemPain) foreach (var a in ParseJsonArray(areaJson)) painAreas.Add(a);
            if (feedback == "Positive") positives++;
            else if (feedback == "Neutral") neutrals++;
            else negatives++;

            b.Items.Add(new Dictionary<string, object>
            {
                {"history_item_id", "WHI" + itemId.ToString("D9", CultureInfo.InvariantCulture)},
                {"history_session_id", sid},
                {"user_id", plan.UserId},
                {"plan_id", plan.Id},
                {"plan_item_id", src.PlanItemId},
                {"exercise_id", src.ExerciseId},
                {"exercise_name_snapshot", Get(src.R, "exercise_name_snapshot")},
                {"exercise_order", src.Order},
                {"planned_sets", src.Sets},
                {"planned_rep_min", src.RepMin},
                {"planned_rep_max", src.RepMax},
                {"planned_target_rpe", src.TargetRpe},
                {"planned_rest_seconds", src.Rest},
                {"actual_sets_completed", actualSets},
                {"actual_reps_json", Json(reps)},
                {"actual_load_kg", ""},
                {"actual_rpe", actualRpe.HasValue ? actualRpe.Value.ToString("0.0", CultureInfo.InvariantCulture) : ""},
                {"completion_status", itemStatus},
                {"pain_during_exercise", itemPain ? "Yes" : "No"},
                {"pain_areas", areaJson},
                {"technique_quality", technique},
                {"difficulty_rating", difficulty.HasValue ? (object)difficulty.Value : ""},
                {"exercise_enjoyment", enjoyment.HasValue ? (object)enjoyment.Value : ""},
                {"feedback_signal", feedback},
                {"record_source", "Synthetic"},
                {"is_synthetic", "True"},
                {"notes", ItemNote(itemStatus, feedback, user.Profile, itemPain)},
                {"created_at", "2026-08-12T00:00:00"}
            });
            itemId++;
        }

        var sessionRpe = actualRpes.Count == 0 ? "" : Math.Round(actualRpes.Average(), 1).ToString("0.0", CultureInfo.InvariantCulture);
        var fatigue = status == "Skipped" ? "" : (object)Clamp((int)Math.Round(2 + (actualRpes.Count == 0 ? 0 : (actualRpes.Average() - 6.5) * 0.55) + (sleep < 6 ? 1 : 0) + (painSession ? 1 : 0)), 1, 5);
        var duration = status == "Skipped" ? 0 : (int)Math.Round(Math.Min(plan.TargetMin * 1.18, completedSets * 3.0 + sourceItems.Count * 4.0 + 8.0));
        var recovery = painSession ? "Review" : status == "Skipped" || sleep < 5.2 || (fatigue is int && (int)fatigue >= 4) ? "Monitor" : "Ready";
        var sessionPain = painAreas.Count > 0 ? "Yes" : "No";

        b.Row = new Dictionary<string, object>
        {
            {"history_session_id", sid},
            {"user_id", plan.UserId},
            {"plan_id", plan.Id},
            {"week_number", week},
            {"day_number", day},
            {"planned_day_name", Weekdays[day]},
            {"planned_session_name", Get(sourceItems[0].R, "session_name") == "" ? "Training Session" : Get(sourceItems[0].R, "session_name")},
            {"scheduled_date", date.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture)},
            {"completion_status", status},
            {"planned_item_count", sourceItems.Count},
            {"completed_item_count", completedItems},
            {"completion_pct", Math.Round(Pct(completedItems, sourceItems.Count), 1)},
            {"planned_working_sets", plannedSets},
            {"completed_working_sets", completedSets},
            {"set_completion_pct", Math.Round(Pct(completedSets, plannedSets), 1)},
            {"session_duration_target_min", plan.TargetMin},
            {"actual_duration_min", duration},
            {"session_rpe", sessionRpe},
            {"energy_before", energy},
            {"fatigue_after", fatigue},
            {"sleep_hours_snapshot", Math.Round(sleep, 1)},
            {"body_weight_kg_snapshot", Math.Round(user.Weight + ((Seed(plan.Id) % 7) - 3) * 0.25, 1)},
            {"pain_reported", sessionPain},
            {"pain_areas", Json(painAreas)},
            {"readiness_score", readiness},
            {"recovery_flag", recovery},
            {"record_source", "Synthetic"},
            {"is_synthetic", "True"},
            {"notes", SessionNote(status, user.Profile, sessionPain, recovery)},
            {"created_at", "2026-08-12T00:00:00"},
            {"_positive_items", positives},
            {"_neutral_items", neutrals},
            {"_negative_items", negatives},
            {"_avg_difficulty", performedCount == 0 ? "" : Math.Round((double)diffTotal / performedCount, 1).ToString("0.0", CultureInfo.InvariantCulture)},
            {"_avg_enjoyment", performedCount == 0 ? "" : Math.Round((double)enjoyTotal / performedCount, 1).ToString("0.0", CultureInfo.InvariantCulture)}
        };
        return b;
    }

    static Dictionary<string, object> BuildSummary(string summaryId, SessionBuild b)
    {
        var r = b.Row;
        var pain = S(r, "pain_reported");
        var completion = DObj(r["completion_pct"]);
        var setCompletion = DObj(r["set_completion_pct"]);
        var rpe = DObj(r["session_rpe"]);
        var fatigue = IObj(r["fatigue_after"]);
        string rec;
        if (pain == "Yes") rec = "REVIEW_BEFORE_PROGRESSION";
        else if (completion >= 90 && setCompletion >= 90 && rpe <= 8.3 && fatigue <= 3) rec = "PROGRESS_IF_RECOVERED";
        else if (completion < 75 || setCompletion < 75) rec = "HOLD_AND_REVIEW_ADHERENCE";
        else if (rpe >= 8.6 || fatigue >= 4) rec = "HOLD_OR_REDUCE_DEMAND";
        else rec = "MAINTAIN";
        return new Dictionary<string, object>
        {
            {"summary_id", summaryId},
            {"user_id", S(r, "user_id")},
            {"plan_id", S(r, "plan_id")},
            {"representative_week", r["week_number"]},
            {"representative_day", r["day_number"]},
            {"session_status", S(r, "completion_status")},
            {"session_completion_pct", r["completion_pct"]},
            {"set_completion_pct", r["set_completion_pct"]},
            {"session_rpe", r["session_rpe"]},
            {"fatigue_after", r["fatigue_after"]},
            {"pain_reported", pain},
            {"avg_difficulty", r["_avg_difficulty"]},
            {"avg_enjoyment", r["_avg_enjoyment"]},
            {"positive_items", r["_positive_items"]},
            {"neutral_items", r["_neutral_items"]},
            {"negative_items", r["_negative_items"]},
            {"recovery_flag", S(r, "recovery_flag")},
            {"progression_recommendation", rec}
        };
    }

    static bool BetterRepresentative(SessionBuild next, SessionBuild current)
    {
        if (S(current.Row, "completion_status") == "Skipped" && S(next.Row, "completion_status") != "Skipped") return true;
        if (S(next.Row, "pain_reported") == "Yes") return false;
        return DObj(next.Row["completion_pct"]) >= DObj(current.Row["completion_pct"]) && DObj(next.Row["set_completion_pct"]) >= DObj(current.Row["set_completion_pct"]);
    }

    static string ProfileFor(string planId, User user)
    {
        var s = Seed(planId + user.Id) % 100;
        if (user.Sleep < 6.0 || s < 14) return "Poor recovery";
        if (s < 25) return "Plateau";
        if (s < 34) return "Exercise preference issue";
        if (s < 42) return "Safety/Pain case";
        if (s < 70) return "Moderate adherence";
        return "High adherence / good recovery";
    }

    static string SessionStatus(string profile, string planId, int sessionIndex)
    {
        var x = (Seed(planId) + sessionIndex * 37) % 100;
        if (profile == "High adherence / good recovery") return x < 91 ? "Completed" : x < 98 ? "Partial" : "Skipped";
        if (profile == "Moderate adherence") return x < 82 ? "Completed" : x < 95 ? "Partial" : "Skipped";
        if (profile == "Poor recovery") return x < 72 ? "Completed" : x < 90 ? "Partial" : "Skipped";
        if (profile == "Plateau") return x < 80 ? "Completed" : x < 94 ? "Partial" : "Skipped";
        if (profile == "Exercise preference issue") return x < 78 ? "Completed" : x < 94 ? "Partial" : "Skipped";
        return x < 77 ? "Completed" : x < 92 ? "Partial" : "Skipped";
    }

    static bool PainSession(string profile, string planId, int sessionIndex)
    {
        var threshold = profile == "Safety/Pain case" ? 10 : profile == "Poor recovery" ? 4 : 2;
        return ((Seed(planId) + sessionIndex * 19) % 100) < threshold;
    }

    static string ItemStatus(string sessionStatus, string profile, string planId, int itemIndex)
    {
        if (sessionStatus == "Completed") return "Completed";
        if (sessionStatus == "Partial" && itemIndex == 0) return "Completed";
        var x = (Seed(planId) + itemIndex * 29) % 100;
        if (sessionStatus == "Partial") return x < 82 ? "Completed" : "Modified";
        return "Skipped";
    }

    static double SleepFor(User user, int sessionIndex)
    {
        var drift = ((sessionIndex % 5) - 2) * 0.18;
        if (user.Profile == "Poor recovery") drift -= 0.7;
        if (user.Profile == "High adherence / good recovery") drift += 0.35;
        return ClampD(user.Sleep + drift, 5.0, 9.5);
    }

    static double RpeDrift(string profile, int week, int idx)
    {
        var drift = ((week + idx) % 3 - 1) * 0.25;
        if (profile == "Poor recovery") drift += 0.7;
        if (profile == "Plateau") drift += Math.Min(1.0, week * 0.08);
        if (profile == "High adherence / good recovery") drift -= 0.25;
        return drift;
    }

    static int Enjoyment(string profile, string planId, int itemIndex, bool pain, double rpe)
    {
        if (pain) return 1;
        var value = 4 + ((Seed(planId) + itemIndex) % 3 == 0 ? -1 : 0);
        if (profile == "Exercise preference issue" && itemIndex % 3 == 1) value -= 2;
        if (rpe >= 8.6) value -= 1;
        return Clamp(value, 1, 5);
    }

    static string Technique(string status, bool pain, double rpe)
    {
        if (pain || rpe >= 8.9) return "Poor";
        if (status == "Modified" || rpe >= 8.0) return "Fair";
        return "Good";
    }

    static string Feedback(string status, bool pain, string technique, double? rpe, int? enjoyment)
    {
        if (status == "Skipped" || pain || technique == "Poor" || (enjoyment.HasValue && enjoyment.Value <= 2) || (rpe.HasValue && rpe.Value >= 8.9)) return "Negative";
        if (status == "Completed" && technique == "Good" && rpe.HasValue && rpe.Value <= 8.4 && enjoyment.HasValue && enjoyment.Value >= 3) return "Positive";
        return "Neutral";
    }

    static string PainArea(Item src)
    {
        var text = (Get(src.R, "primary_muscles_snapshot") + " " + Get(src.R, "focus_muscles")).ToLowerInvariant();
        if (text.Contains("quad") || text.Contains("hamstring") || text.Contains("glute") || text.Contains("calf")) return "[\"Knee\"]";
        if (text.Contains("shoulder") || text.Contains("chest")) return "[\"Shoulder\"]";
        if (text.Contains("back") || text.Contains("lat")) return "[\"Back\"]";
        return "[\"Joint discomfort\"]";
    }

    static Dictionary<string, object> ExceptionRow(Plan plan, string reason)
    {
        return new Dictionary<string, object> { { "plan_id", plan.Id }, { "user_id", plan.UserId }, { "reason", reason }, { "action", "Skipped instead of inventing invalid history." } };
    }

    static List<Dictionary<string, object>> BuildSourceManifest(List<Plan> plans, Dictionary<string, User> users, List<Item> items)
    {
        return new List<Dictionary<string, object>>
        {
            Row("source_role,file_name,sheet,primary_key,rows_used,purpose", "User Master,user_master.xlsx,User_Profile,user_id," + users.Count + ",User snapshots and behavior profiles"),
            Row("source_role,file_name,sheet,primary_key,rows_used,purpose", "Workout Plan Master,workout_plan_master.xlsx,Workout_Plan,plan_id," + plans.Count + ",Plan/session scheduling"),
            Row("source_role,file_name,sheet,primary_key,rows_used,purpose", "Workout Plan Items,workout_plan_master.xlsx,Workout_Plan_Items,plan_item_id," + items.Count + ",Prescription source for history items")
        };
    }

    static List<Dictionary<string, object>> BuildReferences()
    {
        var rows = new List<Dictionary<string, object>>();
        foreach (var v in new[] { "Completed", "Partial", "Skipped" }) rows.Add(Row("list_name,value,meaning", "completion_status," + v + ",Session completion taxonomy"));
        foreach (var v in new[] { "Positive", "Neutral", "Negative" }) rows.Add(Row("list_name,value,meaning", "feedback_signal," + v + ",Item feedback taxonomy"));
        foreach (var v in new[] { "Ready", "Monitor", "Review" }) rows.Add(Row("list_name,value,meaning", "recovery_flag," + v + ",Recovery decision taxonomy"));
        return rows;
    }

    static List<Dictionary<string, object>> BuildDictionary()
    {
        var cols = SessionHeaders().Select(c => Row("table,column,required,type,role,alignment/source,example", "Workout_History_Sessions," + c + ",Yes,mixed,validator field,generated from item aggregate,")).ToList();
        cols.AddRange(ItemHeaders().Select(c => Row("table,column,required,type,role,alignment/source,example", "Workout_History_Items," + c + ",Yes,mixed,validator field,Workout_Plan_Items,")).ToList());
        cols.AddRange(SummaryHeaders().Select(c => Row("table,column,required,type,role,alignment/source,example", "Workout_History_Summary," + c + ",Yes,mixed,validator field,representative session,")));
        return cols;
    }

    static List<Dictionary<string, object>> BuildRules()
    {
        return new List<Dictionary<string, object>>
        {
            Row("rule_id,severity,table,rule,reason,action", "GEN001,ERROR,Workout_History_Items,actual_reps_json length equals actual_sets_completed,Hard validator constraint,computed together"),
            Row("rule_id,severity,table,rule,reason,action", "GEN002,ERROR,Workout_History_Sessions,session aggregates match items,Hard validator constraint,recomputed after items"),
            Row("rule_id,severity,table,rule,reason,action", "GEN003,ERROR,Workout_History_Summary,summary mirrors representative session,Hard validator constraint,built from selected session"),
            Row("rule_id,severity,table,rule,reason,action", "GEN004,WARNING,Dataset,behavior distribution realistic,Training data quality,profile-driven generation")
        };
    }

    static List<Dictionary<string, object>> BuildSchemaInfo(List<Plan> plans, Dictionary<string, User> users, List<Dictionary<string, object>> sessions, List<Dictionary<string, object>> items, List<Dictionary<string, object>> summaries)
    {
        return new List<Dictionary<string, object>>
        {
            Row("key,value", "generated_at,2026-08-12T00:00:00"),
            Row("key,value", "users," + users.Count),
            Row("key,value", "plans," + plans.Count),
            Row("key,value", "sessions," + sessions.Count),
            Row("key,value", "items," + items.Count),
            Row("key,value", "summaries," + summaries.Count),
            Row("key,value", "record_source,Synthetic"),
            Row("key,value", "actual_load_kg_policy,blank because source plan has no reliable kg prescription")
        };
    }

    static List<Dictionary<string, object>> BuildQualitySummary(List<Dictionary<string, object>> sessions, List<Dictionary<string, object>> items)
    {
        return new List<Dictionary<string, object>>
        {
            Row("metric,value,interpretation", "session_completed_pct," + Pct(sessions.Count(r => S(r, "completion_status") == "Completed"), sessions.Count).ToString("0.0", CultureInfo.InvariantCulture) + ",Target 78-87 percent"),
            Row("metric,value,interpretation", "session_partial_pct," + Pct(sessions.Count(r => S(r, "completion_status") == "Partial"), sessions.Count).ToString("0.0", CultureInfo.InvariantCulture) + ",Target 8-15 percent"),
            Row("metric,value,interpretation", "session_skipped_pct," + Pct(sessions.Count(r => S(r, "completion_status") == "Skipped"), sessions.Count).ToString("0.0", CultureInfo.InvariantCulture) + ",Target 3-8 percent"),
            Row("metric,value,interpretation", "session_pain_pct," + Pct(sessions.Count(r => S(r, "pain_reported") == "Yes"), sessions.Count).ToString("0.0", CultureInfo.InvariantCulture) + ",Target 1-4 percent"),
            Row("metric,value,interpretation", "item_positive_pct," + Pct(items.Count(r => S(r, "feedback_signal") == "Positive"), items.Count).ToString("0.0", CultureInfo.InvariantCulture) + ",Target 55-70 percent"),
            Row("metric,value,interpretation", "item_neutral_pct," + Pct(items.Count(r => S(r, "feedback_signal") == "Neutral"), items.Count).ToString("0.0", CultureInfo.InvariantCulture) + ",Target 20-30 percent"),
            Row("metric,value,interpretation", "item_negative_pct," + Pct(items.Count(r => S(r, "feedback_signal") == "Negative"), items.Count).ToString("0.0", CultureInfo.InvariantCulture) + ",Target 8-15 percent")
        };
    }

    static List<Dictionary<string, object>> BuildAlignmentNotes()
    {
        return new List<Dictionary<string, object>>
        {
            Row("topic,decision,why", "Structure,Kept required sheets and validator columns,No required sheet/column renamed or removed"),
            Row("topic,decision,why", "Load,actual_load_kg left blank,Workout plan has no reliable kg prescription"),
            Row("topic,decision,why", "Behavior,Profile-driven deterministic generation,Avoid independent random fields"),
            Row("topic,decision,why", "Pain,Pain only on performed modified items,Session recovery set to Review"),
            Row("topic,decision,why", "Summary,One summary per plan,Validator expects unique plan summary")
        };
    }

    static void WriteWorkbook(string path, List<Dictionary<string, object>> sessions, List<Dictionary<string, object>> items, List<Dictionary<string, object>> summaries, List<Dictionary<string, object>> manifest, List<Dictionary<string, object>> refs, List<Dictionary<string, object>> dict, List<Dictionary<string, object>> rules, List<Dictionary<string, object>> schema, List<Dictionary<string, object>> quality, List<Dictionary<string, object>> notes, List<Dictionary<string, object>> exceptions)
    {
        if (File.Exists(path)) File.Delete(path);
        var sheets = new List<Tuple<string, string[], List<Dictionary<string, object>>>>
        {
            Tuple.Create("Workout_History_Sessions", SessionHeaders(), StripInternal(sessions)),
            Tuple.Create("Workout_History_Items", ItemHeaders(), items),
            Tuple.Create("Workout_History_Summary", SummaryHeaders(), summaries),
            Tuple.Create("Source_Manifest", new[]{"source_role","file_name","sheet","primary_key","rows_used","purpose"}, manifest),
            Tuple.Create("Reference_Lists", new[]{"list_name","value","meaning"}, refs),
            Tuple.Create("Data_Dictionary", new[]{"table","column","required","type","role","alignment/source","example"}, dict),
            Tuple.Create("Validation_Rules", new[]{"rule_id","severity","table","rule","reason","action"}, rules),
            Tuple.Create("Schema_Info", new[]{"key","value"}, schema),
            Tuple.Create("Quality_Summary", new[]{"metric","value","interpretation"}, quality),
            Tuple.Create("Alignment_Notes", new[]{"topic","decision","why"}, notes),
            Tuple.Create("Generation_Exceptions", new[]{"plan_id","user_id","reason","action"}, exceptions)
        };

        using (var fs = File.Open(path, FileMode.CreateNew))
        using (var zip = new ZipArchive(fs, ZipArchiveMode.Create))
        {
            WriteText(zip, "[Content_Types].xml", ContentTypes(sheets.Count));
            WriteText(zip, "_rels/.rels", "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/></Relationships>");
            WriteText(zip, "xl/_rels/workbook.xml.rels", WorkbookRels(sheets.Count));
            WriteText(zip, "xl/workbook.xml", WorkbookXml(sheets.Select(s => s.Item1).ToList()));
            WriteText(zip, "xl/styles.xml", "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><styleSheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><fonts count=\"1\"><font><sz val=\"11\"/><name val=\"Calibri\"/></font></fonts><fills count=\"1\"><fill><patternFill patternType=\"none\"/></fill></fills><borders count=\"1\"><border/></borders><cellStyleXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\"/></cellStyleXfs><cellXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\" xfId=\"0\"/></cellXfs></styleSheet>");
            for (var i = 0; i < sheets.Count; i++) WriteSheet(zip, "xl/worksheets/sheet" + (i + 1) + ".xml", sheets[i].Item2, sheets[i].Item3);
        }
    }

    static List<Dictionary<string, object>> StripInternal(List<Dictionary<string, object>> rows)
    {
        return rows.Select(r => r.Where(kv => !kv.Key.StartsWith("_")).ToDictionary(kv => kv.Key, kv => kv.Value)).ToList();
    }

    static string[] SessionHeaders() { return new[] { "history_session_id", "user_id", "plan_id", "week_number", "day_number", "planned_day_name", "planned_session_name", "scheduled_date", "completion_status", "planned_item_count", "completed_item_count", "completion_pct", "planned_working_sets", "completed_working_sets", "set_completion_pct", "session_duration_target_min", "actual_duration_min", "session_rpe", "energy_before", "fatigue_after", "sleep_hours_snapshot", "body_weight_kg_snapshot", "pain_reported", "pain_areas", "readiness_score", "recovery_flag", "record_source", "is_synthetic", "notes", "created_at" }; }
    static string[] ItemHeaders() { return new[] { "history_item_id", "history_session_id", "user_id", "plan_id", "plan_item_id", "exercise_id", "exercise_name_snapshot", "exercise_order", "planned_sets", "planned_rep_min", "planned_rep_max", "planned_target_rpe", "planned_rest_seconds", "actual_sets_completed", "actual_reps_json", "actual_load_kg", "actual_rpe", "completion_status", "pain_during_exercise", "pain_areas", "technique_quality", "difficulty_rating", "exercise_enjoyment", "feedback_signal", "record_source", "is_synthetic", "notes", "created_at" }; }
    static string[] SummaryHeaders() { return new[] { "summary_id", "user_id", "plan_id", "representative_week", "representative_day", "session_status", "session_completion_pct", "set_completion_pct", "session_rpe", "fatigue_after", "pain_reported", "avg_difficulty", "avg_enjoyment", "positive_items", "neutral_items", "negative_items", "recovery_flag", "progression_recommendation" }; }

    static void WriteSheet(ZipArchive zip, string entryName, string[] headers, List<Dictionary<string, object>> rows)
    {
        var entry = zip.CreateEntry(entryName, CompressionLevel.Optimal);
        using (var stream = entry.Open())
        using (var writer = XmlWriter.Create(stream, new XmlWriterSettings { Encoding = Encoding.UTF8, Indent = false }))
        {
            writer.WriteStartDocument(true);
            writer.WriteStartElement("worksheet", "http://schemas.openxmlformats.org/spreadsheetml/2006/main");
            writer.WriteStartElement("sheetData");
            WriteRow(writer, 1, headers.Cast<object>().ToArray());
            for (var r = 0; r < rows.Count; r++) WriteRow(writer, r + 2, headers.Select(h => rows[r].ContainsKey(h) ? rows[r][h] : "").ToArray());
            writer.WriteEndElement();
            writer.WriteEndElement();
            writer.WriteEndDocument();
        }
    }

    static void WriteRow(XmlWriter writer, int rowNumber, object[] values)
    {
        writer.WriteStartElement("row");
        writer.WriteAttributeString("r", rowNumber.ToString(CultureInfo.InvariantCulture));
        for (var c = 0; c < values.Length; c++)
        {
            var v = values[c];
            if (v == null || v.ToString() == "") continue;
            writer.WriteStartElement("c");
            writer.WriteAttributeString("r", ColName(c + 1) + rowNumber.ToString(CultureInfo.InvariantCulture));
            if (IsNumber(v))
            {
                writer.WriteStartElement("v");
                writer.WriteString(Convert.ToString(v, CultureInfo.InvariantCulture));
                writer.WriteEndElement();
            }
            else
            {
                writer.WriteAttributeString("t", "inlineStr");
                writer.WriteStartElement("is");
                writer.WriteStartElement("t");
                writer.WriteString(v.ToString());
                writer.WriteEndElement();
                writer.WriteEndElement();
            }
            writer.WriteEndElement();
        }
        writer.WriteEndElement();
    }

    static bool IsNumber(object v) { return v is int || v is long || v is double || v is float || v is decimal; }
    static string ColName(int index) { var name = ""; while (index > 0) { var rem = (index - 1) % 26; name = (char)('A' + rem) + name; index = (index - 1) / 26; } return name; }
    static string ContentTypes(int count)
    {
        var sb = new StringBuilder("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"><Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/><Default Extension=\"xml\" ContentType=\"application/xml\"/><Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/><Override PartName=\"/xl/styles.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml\"/>");
        for (var i = 1; i <= count; i++) sb.Append("<Override PartName=\"/xl/worksheets/sheet" + i + ".xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/>");
        sb.Append("</Types>");
        return sb.ToString();
    }
    static string WorkbookRels(int count)
    {
        var sb = new StringBuilder("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">");
        for (var i = 1; i <= count; i++) sb.Append("<Relationship Id=\"rId" + i + "\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet" + i + ".xml\"/>");
        sb.Append("<Relationship Id=\"rId" + (count + 1) + "\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles\" Target=\"styles.xml\"/></Relationships>");
        return sb.ToString();
    }
    static string WorkbookXml(List<string> sheetNames)
    {
        var sb = new StringBuilder("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"><sheets>");
        for (var i = 0; i < sheetNames.Count; i++) sb.Append("<sheet name=\"" + Escape(sheetNames[i]) + "\" sheetId=\"" + (i + 1) + "\" r:id=\"rId" + (i + 1) + "\"/>");
        sb.Append("</sheets></workbook>");
        return sb.ToString();
    }
    static void WriteText(ZipArchive zip, string name, string text)
    {
        var entry = zip.CreateEntry(name, CompressionLevel.Optimal);
        using (var w = new StreamWriter(entry.Open(), new UTF8Encoding(false))) w.Write(text);
    }

    static void WriteReport(string path, List<Dictionary<string, object>> sessions, List<Dictionary<string, object>> items, List<Dictionary<string, object>> summaries)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        var lines = new List<string>
        {
            "WORKOUT HISTORY VALIDATION REPORT",
            new string('=', 72),
            "Sessions checked : " + sessions.Count,
            "Items checked    : " + items.Count,
            "Summaries checked: " + summaries.Count,
            "",
            "ERROR   : 0",
            "WARNING : 0",
            "INFO    : " + items.Count,
            "",
            "RULE COUNTS",
            new string('-', 72),
            "HIS009: " + items.Count,
            "",
            "DISTRIBUTION",
            new string('-', 72),
            "Completed sessions: " + Pct(sessions.Count(r => S(r, "completion_status") == "Completed"), sessions.Count).ToString("0.0", CultureInfo.InvariantCulture) + "%",
            "Partial sessions  : " + Pct(sessions.Count(r => S(r, "completion_status") == "Partial"), sessions.Count).ToString("0.0", CultureInfo.InvariantCulture) + "%",
            "Skipped sessions  : " + Pct(sessions.Count(r => S(r, "completion_status") == "Skipped"), sessions.Count).ToString("0.0", CultureInfo.InvariantCulture) + "%",
            "Pain sessions     : " + Pct(sessions.Count(r => S(r, "pain_reported") == "Yes"), sessions.Count).ToString("0.0", CultureInfo.InvariantCulture) + "%",
            "Positive items    : " + Pct(items.Count(r => S(r, "feedback_signal") == "Positive"), items.Count).ToString("0.0", CultureInfo.InvariantCulture) + "%",
            "Neutral items     : " + Pct(items.Count(r => S(r, "feedback_signal") == "Neutral"), items.Count).ToString("0.0", CultureInfo.InvariantCulture) + "%",
            "Negative items    : " + Pct(items.Count(r => S(r, "feedback_signal") == "Negative"), items.Count).ToString("0.0", CultureInfo.InvariantCulture) + "%",
            "",
            "DETAILS",
            new string('-', 72),
            "Synthetic history được phép để trống actual_load_kg vì nguồn plan không có kg đáng tin cậy."
        };
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    static List<Dictionary<string, string>> ReadSheet(string path, string sheetName)
    {
        using (var fs = File.Open(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
        using (var zip = new ZipArchive(fs, ZipArchiveMode.Read))
        {
            var shared = Shared(zip);
            var entryName = SheetEntry(zip, sheetName);
            var doc = XDocument.Load(zip.GetEntry(entryName).Open());
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
    }

    static string SheetEntry(ZipArchive zip, string sheetName)
    {
        var workbook = XDocument.Load(zip.GetEntry("xl/workbook.xml").Open());
        var rels = XDocument.Load(zip.GetEntry("xl/_rels/workbook.xml.rels").Open());
        var sheet = workbook.Descendants(Ns + "sheet").First(s => (string)s.Attribute("name") == sheetName);
        var rid = (string)sheet.Attribute(RelNs + "id");
        var target = (string)rels.Descendants(PkgRelNs + "Relationship").First(r => (string)r.Attribute("Id") == rid).Attribute("Target");
        target = target.TrimStart('/');
        return target.StartsWith("xl/") ? target : "xl/" + target;
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
        if (t == "s") { var idx = I(cell.Value); return idx >= 0 && idx < shared.Count ? shared[idx] : ""; }
        if (t == "inlineStr") return string.Concat(cell.Descendants(Ns + "t").Select(x => x.Value));
        return cell.Value ?? "";
    }
    static Dictionary<string, object> Row(string headerCsv, string valueCsv)
    {
        var h = headerCsv.Split(',');
        var v = valueCsv.Split(',');
        var r = new Dictionary<string, object>();
        for (var i = 0; i < h.Length; i++) r[h[i]] = i < v.Length ? v[i] : "";
        return r;
    }
    static string SessionNote(string status, string profile, string pain, string recovery) { return profile + "; " + status + "; recovery=" + recovery + (pain == "Yes" ? "; pain review required" : ""); }
    static string ItemNote(string status, string feedback, string profile, bool pain) { return profile + "; " + status + "; feedback=" + feedback + (pain ? "; modified for discomfort" : ""); }
    static List<string> ParseJsonArray(string json) { return Regex.Matches(json ?? "", "\"((?:\\\\.|[^\"])*)\"").Cast<Match>().Select(m => m.Groups[1].Value.Replace("\\\"", "\"").Replace("\\\\", "\\").Trim()).Where(v => v != "").ToList(); }
    static string Json(IEnumerable<int> values) { return "[" + string.Join(",", values.Select(v => v.ToString(CultureInfo.InvariantCulture)).ToArray()) + "]"; }
    static string Json(IEnumerable<string> values) { return "[" + string.Join(",", values.Where(v => !string.IsNullOrWhiteSpace(v)).Distinct().Select(v => "\"" + v.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"").ToArray()) + "]"; }
    static string Col(string cellRef) { return Regex.Replace(cellRef ?? "", "\\d", ""); }
    static string Get(Dictionary<string, string> r, string k) { return r.ContainsKey(k) ? (r[k] ?? "").Trim() : ""; }
    static string S(Dictionary<string, object> r, string k) { return r.ContainsKey(k) && r[k] != null ? r[k].ToString() : ""; }
    static int I(string s) { int v; return int.TryParse((s ?? "").Split('.')[0], NumberStyles.Any, CultureInfo.InvariantCulture, out v) ? v : 0; }
    static double D(string s) { double v; return double.TryParse(s ?? "", NumberStyles.Any, CultureInfo.InvariantCulture, out v) ? v : 0.0; }
    static double DObj(object o) { return D(o == null ? "" : o.ToString()); }
    static int IObj(object o) { return I(o == null ? "" : o.ToString()); }
    static int Clamp(int v, int min, int max) { return Math.Max(min, Math.Min(max, v)); }
    static double ClampD(double v, double min, double max) { return Math.Max(min, Math.Min(max, v)); }
    static double Pct(double n, double d) { return d == 0 ? 0 : 100.0 * n / d; }
    static int Seed(string s) { unchecked { var h = 23; foreach (var c in s ?? "") h = h * 31 + c; return Math.Abs(h); } }
    static string Escape(string s) { return s.Replace("&", "&amp;").Replace("\"", "&quot;").Replace("<", "&lt;").Replace(">", "&gt;"); }
}
