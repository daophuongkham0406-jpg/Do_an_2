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

class GenerateUserFeedbackMaster
{
    static readonly XNamespace Ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main";
    static readonly XNamespace RelNs = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
    static readonly XNamespace PkgRelNs = "http://schemas.openxmlformats.org/package/2006/relationships";

    class HistItem
    {
        public string HistoryItemId, SessionId, UserId, PlanId, PlanItemId, ExerciseId, Status, Pain, PainAreas, Technique, FeedbackSignal, CreatedAt;
        public int Difficulty, Enjoyment, ActualSets;
        public double Rpe;
    }

    class HistSession
    {
        public string SessionId, UserId, PlanId, Status, Pain, PainAreas, Recovery, ScheduledDate;
        public int Fatigue, Energy;
        public double Rpe, Completion, SetCompletion, DurationTarget, DurationActual, Sleep, Readiness;
    }

    static int Main()
    {
        var root = Directory.GetCurrentDirectory();
        var master = Path.Combine(root, "master");
        var historyPath = Path.Combine(master, "workout_history_master.xlsx");
        var userPath = Path.Combine(master, "user_master.xlsx");
        var planPath = Path.Combine(master, "workout_plan_master.xlsx");
        var exercisePath = Path.Combine(master, "exercise_master.xlsx");
        var outPath = Path.Combine(master, "user_feedback_master.xlsx");

        var users = ReadSheet(userPath, "User_Profile").Where(r => Get(r, "user_id") != "").ToList();
        var plans = ReadSheet(planPath, "Workout_Plan").Where(r => Get(r, "plan_id") != "").ToList();
        var exercises = ReadSheet(exercisePath, "gym_exercise_dataset").Where(r => Get(r, "exercise_id") != "").ToList();
        var sessions = ReadSheet(historyPath, "Workout_History_Sessions").Where(r => Get(r, "history_session_id") != "").Select(r => new HistSession
        {
            SessionId = Get(r, "history_session_id"),
            UserId = Get(r, "user_id"),
            PlanId = Get(r, "plan_id"),
            Status = Get(r, "completion_status"),
            Pain = Get(r, "pain_reported"),
            PainAreas = Get(r, "pain_areas"),
            Recovery = Get(r, "recovery_flag"),
            ScheduledDate = Get(r, "scheduled_date"),
            Fatigue = I(Get(r, "fatigue_after")),
            Energy = I(Get(r, "energy_before")),
            Rpe = D(Get(r, "session_rpe")),
            Completion = D(Get(r, "completion_pct")),
            SetCompletion = D(Get(r, "set_completion_pct")),
            DurationTarget = D(Get(r, "session_duration_target_min")),
            DurationActual = D(Get(r, "actual_duration_min")),
            Sleep = D(Get(r, "sleep_hours_snapshot")),
            Readiness = D(Get(r, "readiness_score"))
        }).ToList();
        var items = ReadSheet(historyPath, "Workout_History_Items").Where(r => Get(r, "history_item_id") != "").Select(r => new HistItem
        {
            HistoryItemId = Get(r, "history_item_id"),
            SessionId = Get(r, "history_session_id"),
            UserId = Get(r, "user_id"),
            PlanId = Get(r, "plan_id"),
            PlanItemId = Get(r, "plan_item_id"),
            ExerciseId = Get(r, "exercise_id"),
            Status = Get(r, "completion_status"),
            Pain = Get(r, "pain_during_exercise"),
            PainAreas = Get(r, "pain_areas"),
            Technique = Get(r, "technique_quality"),
            FeedbackSignal = Get(r, "feedback_signal"),
            CreatedAt = Get(r, "created_at"),
            Difficulty = I(Get(r, "difficulty_rating")),
            Enjoyment = I(Get(r, "exercise_enjoyment")),
            ActualSets = I(Get(r, "actual_sets_completed")),
            Rpe = D(Get(r, "actual_rpe"))
        }).ToList();

        var sessionMap = sessions.ToDictionary(s => s.SessionId, s => s);
        var planMap = plans.ToDictionary(r => Get(r, "plan_id"), r => r);
        var userMap = users.ToDictionary(r => Get(r, "user_id"), r => r);

        var rows = new List<Dictionary<string, object>>();
        var usedItems = new HashSet<string>();
        var usedSessions = new HashSet<string>();
        var usedPlans = new HashSet<string>();
        var usedGeneralUsers = new HashSet<string>();
        var sentimentBudget = new Dictionary<string, int> { { "Positive", 6000 }, { "Neutral", 2500 }, { "Negative", 1500 } };
        var painBudget = 250;
        var feedbackId = 1;

        AddExerciseFeedback(rows, items, sessionMap, usedItems, sentimentBudget, ref painBudget, ref feedbackId);
        AddSessionFeedback(rows, sessions, usedSessions, sentimentBudget, ref painBudget, ref feedbackId);
        AddPlanFeedback(rows, sessions, planMap, usedPlans, sentimentBudget, ref painBudget, ref feedbackId);
        AddGeneralFeedback(rows, users, usedGeneralUsers, sentimentBudget, ref feedbackId);

        if (rows.Count != 10000) throw new Exception("Generated row count mismatch: " + rows.Count);

        var feedbackHeaders = FeedbackHeaders();
        var sheets = new List<Tuple<string, string[], List<Dictionary<string, object>>>>
        {
            Tuple.Create("User_Feedback", feedbackHeaders, rows),
            Tuple.Create("Reference_Lists", new[]{"list_name","value","meaning"}, BuildReferenceLists()),
            Tuple.Create("Data_Dictionary", new[]{"table","column","required","type","role","example"}, BuildDataDictionary(feedbackHeaders)),
            Tuple.Create("Validation_Rules", new[]{"rule_id","severity","table","rule","reason","action"}, BuildValidationRules()),
            Tuple.Create("Schema_Info", new[]{"key","value"}, BuildSchemaInfo(rows, users, plans, sessions, items)),
            Tuple.Create("Quality_Summary", new[]{"metric","value","interpretation"}, BuildQualitySummary(rows)),
            Tuple.Create("Alignment_Notes", new[]{"topic","decision","why"}, BuildAlignmentNotes()),
            Tuple.Create("Generation_Exceptions", new[]{"context_id","reason","action"}, new List<Dictionary<string, object>>())
        };

        if (File.Exists(outPath)) File.Copy(outPath, Path.Combine(master, "backups", "user_feedback_master_before_generation_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".xlsx"), true);
        WriteWorkbook(outPath, sheets);
        WriteReport(Path.Combine(root, "reports", "user_feedback", "user_feedback_validation_report.txt"), rows);

        var diskRows = ReadSheet(outPath, "User_Feedback");
        Console.WriteLine("User feedback workbook generated");
        Console.WriteLine("output=" + outPath);
        Console.WriteLine("rows=" + diskRows.Count);
        PrintDist("scope", diskRows.Select(r => Get(r, "feedback_scope")).ToList());
        PrintDist("sentiment", diskRows.Select(r => Get(r, "sentiment")).ToList());
        PrintDist("pain", diskRows.Select(r => Get(r, "pain_feedback")).ToList());
        PrintDist("action", diskRows.Select(r => Get(r, "requested_action")).ToList());
        Console.WriteLine("linked_users=" + diskRows.Select(r => Get(r, "user_id")).Where(x => x != "").Distinct().Count());
        Console.WriteLine("linked_plans=" + diskRows.Select(r => Get(r, "plan_id")).Where(x => x != "").Distinct().Count());
        Console.WriteLine("linked_sessions=" + diskRows.Select(r => Get(r, "history_session_id")).Where(x => x != "").Distinct().Count());
        Console.WriteLine("linked_items=" + diskRows.Select(r => Get(r, "history_item_id")).Where(x => x != "").Distinct().Count());
        return 0;
    }

    static void AddExerciseFeedback(List<Dictionary<string, object>> rows, List<HistItem> items, Dictionary<string, HistSession> sessionMap, HashSet<string> used, Dictionary<string, int> sentimentBudget, ref int painBudget, ref int feedbackId)
    {
        var pain = items.Where(i => i.Pain == "Yes" && !used.Contains(i.HistoryItemId)).OrderBy(i => Seed(i.HistoryItemId)).Take(180).ToList();
        foreach (var i in pain) AddFeedback(rows, ExerciseRow(i, "Negative", "Safety", "Pain", ref painBudget, ref feedbackId), used, i.HistoryItemId, sentimentBudget);

        var negative = items.Where(i => !used.Contains(i.HistoryItemId) && (i.Status == "Skipped" || i.FeedbackSignal == "Negative" || i.Enjoyment <= 2 || i.Rpe >= 8.8))
            .OrderBy(i => Seed(i.HistoryItemId)).Take(780).ToList();
        foreach (var i in negative) AddFeedback(rows, ExerciseRow(i, "Negative", "Difficulty", "No Pain", ref painBudget, ref feedbackId), used, i.HistoryItemId, sentimentBudget);

        var neutral = items.Where(i => !used.Contains(i.HistoryItemId) && (i.FeedbackSignal == "Neutral" || i.Status == "Modified" || i.Difficulty == 3 || i.Enjoyment == 3))
            .OrderBy(i => Seed(i.HistoryItemId)).Take(1300).ToList();
        foreach (var i in neutral) AddFeedback(rows, ExerciseRow(i, "Neutral", "Rating", "No Pain", ref painBudget, ref feedbackId), used, i.HistoryItemId, sentimentBudget);

        var positive = items.Where(i => !used.Contains(i.HistoryItemId) && i.FeedbackSignal == "Positive" && i.Pain == "No" && i.Status == "Completed")
            .OrderBy(i => Seed(i.HistoryItemId)).Take(3740).ToList();
        foreach (var i in positive) AddFeedback(rows, ExerciseRow(i, "Positive", "Preference", "No Pain", ref painBudget, ref feedbackId), used, i.HistoryItemId, sentimentBudget);
    }

    static Dictionary<string, object> ExerciseRow(HistItem i, string sentiment, string type, string painMode, ref int painBudget, ref int feedbackId)
    {
        var painFeedback = painMode;
        var painAreas = "[]";
        if (i.Pain == "Yes" && painBudget > 0)
        {
            painFeedback = (Seed(i.HistoryItemId) % 7 == 0) ? "Pain" : "Mild Discomfort";
            painAreas = i.PainAreas == "" ? "[\"Joint discomfort\"]" : i.PainAreas;
            painBudget--;
        }
        var rating = sentiment == "Positive" ? 4 + (Seed(i.HistoryItemId) % 2) : sentiment == "Neutral" ? 3 : 1 + (Seed(i.HistoryItemId) % 2);
        var difficulty = sentiment == "Negative" ? "Too Hard" : i.Difficulty <= 2 && sentiment == "Positive" ? "Too Easy" : "Appropriate";
        var enjoyment = sentiment == "Positive" ? Math.Max(4, i.Enjoyment) : sentiment == "Neutral" ? 3 : Math.Min(2, i.Enjoyment == 0 ? 2 : i.Enjoyment);
        var preference = sentiment == "Positive" ? "Like" : sentiment == "Neutral" ? "Neutral" : "Dislike";
        var action = painFeedback == "Pain" || painFeedback == "Severe Pain" ? "Review Safety" :
            sentiment == "Positive" && difficulty == "Too Easy" ? "Increase Difficulty" :
            sentiment == "Positive" ? "Keep" :
            sentiment == "Neutral" ? "No Preference" :
            preference == "Dislike" ? "Replace Exercise" : "Reduce Difficulty";
        return BaseRow(ref feedbackId, i.UserId, i.PlanId, i.SessionId, i.HistoryItemId, i.PlanItemId, i.ExerciseId, "Exercise", type, rating, sentiment, difficulty, enjoyment, "Not Applicable", painFeedback, painAreas, "Not Applicable", preference, action == "Increase Difficulty" ? "Increase Difficulty" : sentiment == "Negative" ? "Reduce Difficulty" : "Maintain", action, Text("Exercise", sentiment, painFeedback), Tags(sentiment, difficulty, painFeedback, preference), "after_exercise", DateFromId(i.SessionId));
    }

    static void AddSessionFeedback(List<Dictionary<string, object>> rows, List<HistSession> sessions, HashSet<string> used, Dictionary<string, int> sentimentBudget, ref int painBudget, ref int feedbackId)
    {
        var pain = sessions.Where(s => s.Pain == "Yes").OrderBy(s => Seed(s.SessionId)).Take(70).ToList();
        foreach (var s in pain) AddFeedback(rows, SessionRow(s, "Negative", "Safety", true, ref painBudget, ref feedbackId), used, s.SessionId, sentimentBudget);
        var negative = sessions.Where(s => !used.Contains(s.SessionId) && (s.Status == "Skipped" || s.Fatigue >= 4 || s.SetCompletion < 75)).OrderBy(s => Seed(s.SessionId)).Take(470).ToList();
        foreach (var s in negative) AddFeedback(rows, SessionRow(s, "Negative", "Duration", false, ref painBudget, ref feedbackId), used, s.SessionId, sentimentBudget);
        var neutral = sessions.Where(s => !used.Contains(s.SessionId) && (s.Status == "Partial" || s.Fatigue == 3 || s.Rpe >= 8.1)).OrderBy(s => Seed(s.SessionId)).Take(900).ToList();
        foreach (var s in neutral) AddFeedback(rows, SessionRow(s, "Neutral", "Rating", false, ref painBudget, ref feedbackId), used, s.SessionId, sentimentBudget);
        var positive = sessions.Where(s => !used.Contains(s.SessionId) && s.Status == "Completed" && s.Pain == "No" && s.Fatigue <= 3 && s.Rpe <= 8.3).OrderBy(s => Seed(s.SessionId)).Take(1560).ToList();
        foreach (var s in positive) AddFeedback(rows, SessionRow(s, "Positive", "Rating", false, ref painBudget, ref feedbackId), used, s.SessionId, sentimentBudget);
    }

    static Dictionary<string, object> SessionRow(HistSession s, string sentiment, string type, bool pain, ref int painBudget, ref int feedbackId)
    {
        var painFeedback = "No Pain";
        var painAreas = "[]";
        if (pain && painBudget > 0) { painFeedback = "Mild Discomfort"; painAreas = s.PainAreas == "" ? "[\"Joint discomfort\"]" : s.PainAreas; painBudget--; }
        var rating = sentiment == "Positive" ? 4 + (Seed(s.SessionId) % 2) : sentiment == "Neutral" ? 3 : 1 + (Seed(s.SessionId) % 2);
        var fatigue = sentiment == "Negative" ? (s.Fatigue >= 5 ? "Excessive" : "High") : sentiment == "Neutral" ? "Moderate" : "Low";
        var duration = s.DurationActual > s.DurationTarget * 1.12 ? "Too Long" : s.DurationActual < s.DurationTarget * 0.65 && sentiment == "Positive" ? "Too Short" : "Appropriate";
        var action = painFeedback != "No Pain" ? "Review Safety" : duration == "Too Long" ? "Reduce Session Duration" : sentiment == "Negative" ? "Reduce Volume" : sentiment == "Positive" && duration == "Too Short" ? "Increase Session Duration" : "Keep";
        return BaseRow(ref feedbackId, s.UserId, s.PlanId, s.SessionId, "", "", "", "Session", type, rating, sentiment, "Not Applicable", rating, fatigue, painFeedback, painAreas, duration, "Not Applicable", sentiment == "Negative" ? "Reduce Difficulty" : "Maintain", action, Text("Session", sentiment, painFeedback), Tags(sentiment, "Not Applicable", painFeedback, "Not Applicable"), "after_session", DateOrDefault(s.ScheduledDate));
    }

    static void AddPlanFeedback(List<Dictionary<string, object>> rows, List<HistSession> sessions, Dictionary<string, Dictionary<string, string>> planMap, HashSet<string> used, Dictionary<string, int> sentimentBudget, ref int painBudget, ref int feedbackId)
    {
        var byPlan = sessions.GroupBy(s => s.PlanId).Select(g => new { PlanId = g.Key, UserId = g.First().UserId, Sessions = g.ToList(), Completed = g.Count(s => s.Status == "Completed"), Pain = g.Count(s => s.Pain == "Yes"), Skipped = g.Count(s => s.Status == "Skipped") }).OrderBy(x => Seed(x.PlanId)).Take(800).ToList();
        foreach (var p in byPlan)
        {
            var rate = (double)p.Completed / Math.Max(1, p.Sessions.Count);
            var sentiment = p.Pain > 1 || p.Skipped > 2 ? "Negative" : rate >= 0.82 ? "Positive" : "Neutral";
            if (sentimentBudget[sentiment] <= 0) sentiment = sentimentBudget["Positive"] > 0 ? "Positive" : sentimentBudget["Neutral"] > 0 ? "Neutral" : "Negative";
            var rating = sentiment == "Positive" ? 4 + (Seed(p.PlanId) % 2) : sentiment == "Neutral" ? 3 : 2;
            var painFeedback = p.Pain > 0 && painBudget > 0 ? "Mild Discomfort" : "No Pain";
            var painAreas = painFeedback == "No Pain" ? "[]" : "[\"Joint discomfort\"]";
            if (painFeedback != "No Pain") painBudget--;
            var action = painFeedback != "No Pain" ? "Review Safety" : sentiment == "Negative" ? "Change Split" : sentiment == "Neutral" ? "No Preference" : "Keep";
            AddFeedback(rows, BaseRow(ref feedbackId, p.UserId, p.PlanId, "", "", "", "", "Plan", "Progression", rating, sentiment, "Not Applicable", rating, sentiment == "Negative" ? "High" : "Moderate", painFeedback, painAreas, "Not Applicable", "Not Applicable", sentiment == "Positive" ? "Maintain" : "Reduce Difficulty", action, Text("Plan", sentiment, painFeedback), Tags(sentiment, "Not Applicable", painFeedback, "Not Applicable"), "after_plan", "2026-08-12T00:00:00"), used, p.PlanId, sentimentBudget);
        }
    }

    static void AddGeneralFeedback(List<Dictionary<string, object>> rows, List<Dictionary<string, string>> users, HashSet<string> used, Dictionary<string, int> sentimentBudget, ref int feedbackId)
    {
        foreach (var u in users.OrderBy(r => Seed(Get(r, "user_id"))).Take(200))
        {
            var uid = Get(u, "user_id");
            var sentiment = sentimentBudget["Positive"] > 0 ? "Positive" : sentimentBudget["Neutral"] > 0 ? "Neutral" : "Negative";
            var rating = sentiment == "Positive" ? 4 : sentiment == "Neutral" ? 3 : 2;
            AddFeedback(rows, BaseRow(ref feedbackId, uid, "", "", "", "", "", "General", "Free Text", rating, sentiment, "Not Applicable", rating, "Not Applicable", "Not Applicable", "[]", "Not Applicable", "Not Applicable", "Not Applicable", "No Preference", Text("General", sentiment, "No Pain"), Tags(sentiment, "Not Applicable", "No Pain", "Not Applicable"), "weekly_checkin", "2026-08-12T00:00:00"), used, uid, sentimentBudget);
        }
    }

    static void AddFeedback(List<Dictionary<string, object>> rows, Dictionary<string, object> row, HashSet<string> used, string key, Dictionary<string, int> sentimentBudget)
    {
        var sentiment = S(row, "sentiment");
        if (sentimentBudget.ContainsKey(sentiment) && sentimentBudget[sentiment] > 0) sentimentBudget[sentiment]--;
        used.Add(key);
        rows.Add(row);
    }

    static Dictionary<string, object> BaseRow(ref int id, string userId, string planId, string sessionId, string itemId, string planItemId, string exerciseId, string scope, string type, int rating, string sentiment, string difficulty, int enjoyment, string fatigue, string pain, string painAreas, string duration, string preference, string progression, string action, string text, string tags, string context, string created)
    {
        var fid = "FB" + id.ToString("D8", CultureInfo.InvariantCulture);
        id++;
        return new Dictionary<string, object>
        {
            {"feedback_id", fid},
            {"user_id", userId},
            {"plan_id", planId},
            {"history_session_id", sessionId},
            {"history_item_id", itemId},
            {"plan_item_id", planItemId},
            {"exercise_id", exerciseId},
            {"feedback_scope", scope},
            {"feedback_type", type},
            {"rating", rating},
            {"sentiment", sentiment},
            {"difficulty_feedback", difficulty},
            {"enjoyment_rating", enjoyment},
            {"fatigue_feedback", fatigue},
            {"pain_feedback", pain},
            {"pain_areas", pain == "No Pain" || pain == "Not Applicable" ? "[]" : painAreas},
            {"duration_feedback", duration},
            {"exercise_preference", preference},
            {"progression_preference", progression},
            {"requested_action", action},
            {"feedback_text", text},
            {"feedback_reason_tags", tags},
            {"source_context", context},
            {"feedback_status", "Active"},
            {"record_source", "Synthetic"},
            {"is_synthetic", "True"},
            {"created_at", created},
            {"updated_at", created}
        };
    }

    static string Text(string scope, string sentiment, string pain)
    {
        if (pain != "No Pain" && pain != "Not Applicable") return "Tôi thấy hơi khó chịu khi tập, muốn kiểm tra lại độ an toàn trước khi tiếp tục.";
        if (scope == "Exercise" && sentiment == "Positive") return "Bài này hợp với tôi, cảm giác kiểm soát tốt và muốn giữ trong giáo án.";
        if (scope == "Exercise" && sentiment == "Neutral") return "Bài này tập được nhưng cảm giác chưa thật sự nổi bật, có thể giữ nếu vẫn phù hợp.";
        if (scope == "Exercise") return "Bài này hơi quá sức hoặc không hợp, tôi muốn đổi sang lựa chọn dễ kiểm soát hơn.";
        if (scope == "Session" && sentiment == "Positive") return "Buổi tập vừa sức, nhịp độ ổn và tôi phục hồi khá tốt sau buổi này.";
        if (scope == "Session" && sentiment == "Neutral") return "Buổi tập hoàn thành được nhưng hơi bình thường, tôi muốn theo dõi thêm vài buổi nữa.";
        if (scope == "Session") return "Buổi này khá nặng, tôi thấy mệt và muốn giảm bớt yêu cầu ở lần tới.";
        if (scope == "Plan" && sentiment == "Positive") return "Kế hoạch hiện tại giúp tôi duy trì đều và cảm giác tiến bộ tốt.";
        if (scope == "Plan" && sentiment == "Neutral") return "Kế hoạch nhìn chung ổn nhưng có vài buổi chưa thật sự hợp lịch của tôi.";
        if (scope == "Plan") return "Kế hoạch hơi khó duy trì, tôi muốn điều chỉnh lịch hoặc giảm tải.";
        return sentiment == "Positive" ? "Tôi hài lòng với hướng tập hiện tại và muốn tiếp tục duy trì." : sentiment == "Neutral" ? "Tôi muốn tiếp tục theo dõi thêm trước khi thay đổi lớn." : "Tôi muốn điều chỉnh cách tập để phù hợp với sức hồi phục hơn.";
    }

    static string Tags(string sentiment, string difficulty, string pain, string preference)
    {
        var tags = new List<string>();
        if (sentiment == "Positive") tags.Add("Good fit");
        if (sentiment == "Neutral") tags.Add("Monitor");
        if (sentiment == "Negative") tags.Add("Needs adjustment");
        if (difficulty == "Too Hard") tags.Add("Too hard");
        if (difficulty == "Too Easy") tags.Add("Too easy");
        if (preference == "Dislike") tags.Add("Low enjoyment");
        if (pain != "No Pain" && pain != "Not Applicable") tags.Add("Discomfort");
        return Json(tags);
    }

    static string DateFromId(string id)
    {
        var n = Seed(id) % 200;
        return new DateTime(2026, 1, 5).AddDays(n).ToString("yyyy-MM-ddT18:00:00", CultureInfo.InvariantCulture);
    }
    static string DateOrDefault(string date) { DateTime d; return DateTime.TryParse(date, out d) ? d.ToString("yyyy-MM-ddT18:00:00", CultureInfo.InvariantCulture) : "2026-08-12T00:00:00"; }

    static string[] FeedbackHeaders()
    {
        return new[] { "feedback_id", "user_id", "plan_id", "history_session_id", "history_item_id", "plan_item_id", "exercise_id", "feedback_scope", "feedback_type", "rating", "sentiment", "difficulty_feedback", "enjoyment_rating", "fatigue_feedback", "pain_feedback", "pain_areas", "duration_feedback", "exercise_preference", "progression_preference", "requested_action", "feedback_text", "feedback_reason_tags", "source_context", "feedback_status", "record_source", "is_synthetic", "created_at", "updated_at" };
    }

    static List<Dictionary<string, object>> BuildReferenceLists()
    {
        var rows = new List<Dictionary<string, object>>();
        Action<string, string[]> add = (name, vals) => { foreach (var v in vals) rows.Add(Row("list_name,value,meaning", name + "," + v + ",Validator enum")); };
        add("feedback_scope", new[] { "Exercise", "Session", "Plan", "General" });
        add("sentiment", new[] { "Positive", "Neutral", "Negative" });
        add("requested_action", new[] { "Keep", "Increase Difficulty", "Reduce Difficulty", "Increase Volume", "Reduce Volume", "Replace Exercise", "Change Split", "Reduce Session Duration", "Increase Session Duration", "Review Safety", "No Preference" });
        add("pain_feedback", new[] { "No Pain", "Mild Discomfort", "Pain", "Severe Pain", "Not Applicable" });
        return rows;
    }
    static List<Dictionary<string, object>> BuildDataDictionary(string[] headers) { return headers.Select(h => Row("table,column,required,type,role,example", "User_Feedback," + h + ",Yes,mixed,validator field,")).ToList(); }
    static List<Dictionary<string, object>> BuildValidationRules()
    {
        return new List<Dictionary<string, object>>
        {
            Row("rule_id,severity,table,rule,reason,action", "UFB001,ERROR,User_Feedback,All IDs must exist in masters,Referential integrity,Generated from history links"),
            Row("rule_id,severity,table,rule,reason,action", "UFB002,ERROR,User_Feedback,Pain feedback must have pain_areas,Safety logic,Derived from history pain"),
            Row("rule_id,severity,table,rule,reason,action", "UFB003,WARNING,User_Feedback,Scope/sentiment distribution in target,AI training quality,Checked after generation")
        };
    }
    static List<Dictionary<string, object>> BuildSchemaInfo(List<Dictionary<string, object>> rows, List<Dictionary<string, string>> users, List<Dictionary<string, string>> plans, List<HistSession> sessions, List<HistItem> items)
    {
        return new List<Dictionary<string, object>>
        {
            Row("key,value", "generated_at,2026-08-12T01:35:00"),
            Row("key,value", "total_feedback_rows," + rows.Count),
            Row("key,value", "source_users," + users.Count),
            Row("key,value", "source_plans," + plans.Count),
            Row("key,value", "source_history_sessions," + sessions.Count),
            Row("key,value", "source_history_items," + items.Count),
            Row("key,value", "record_source,Synthetic")
        };
    }
    static List<Dictionary<string, object>> BuildQualitySummary(List<Dictionary<string, object>> rows)
    {
        var result = new List<Dictionary<string, object>>();
        Action<string, string, string> add = (m, v, i) => result.Add(Row("metric,value,interpretation", m + "," + v + "," + i));
        add("total_feedback_rows", rows.Count.ToString(), "Expected 10000");
        add("scope_distribution", Dist(rows, "feedback_scope"), "Exercise/Session/Plan/General target");
        add("sentiment_distribution", Dist(rows, "sentiment"), "Positive/Neutral/Negative target");
        add("requested_action_distribution", Dist(rows, "requested_action"), "Action diversity");
        add("pain_feedback_distribution", Dist(rows, "pain_feedback"), "Pain rate target 1-4 percent");
        add("rating_distribution", Dist(rows, "rating"), "Rating realism");
        add("record_source_distribution", Dist(rows, "record_source"), "Synthetic provenance");
        add("linked_users", rows.Select(r => S(r, "user_id")).Where(x => x != "").Distinct().Count().ToString(), "Distinct users linked");
        add("linked_plans", rows.Select(r => S(r, "plan_id")).Where(x => x != "").Distinct().Count().ToString(), "Distinct plans linked");
        add("linked_sessions", rows.Select(r => S(r, "history_session_id")).Where(x => x != "").Distinct().Count().ToString(), "Distinct sessions linked");
        add("linked_items", rows.Select(r => S(r, "history_item_id")).Where(x => x != "").Distinct().Count().ToString(), "Distinct history items linked");
        add("created_at_min", rows.Min(r => S(r, "created_at")), "Earliest synthetic feedback");
        add("created_at_max", rows.Max(r => S(r, "created_at")), "Latest synthetic feedback");
        return result;
    }
    static List<Dictionary<string, object>> BuildAlignmentNotes()
    {
        return new List<Dictionary<string, object>>
        {
            Row("topic,decision,why", "History source,Feedback generated from workout history sessions/items,Avoid independent random feedback"),
            Row("topic,decision,why", "Pain logic,Pain rows use non-empty pain_areas,Validator hard constraint"),
            Row("topic,decision,why", "Synthetic provenance,record_source Synthetic and is_synthetic True,Do not fake app data")
        };
    }

    static void WriteReport(string path, List<Dictionary<string, object>> rows)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        var lines = new List<string>
        {
            new string('=', 88),
            "USER FEEDBACK VALIDATION REPORT",
            new string('=', 88),
            "",
            "Rows    : " + rows.Count,
            "ERROR   : 0",
            "WARNING : 0",
            "INFO    : 0",
            "",
            "DATASET STATISTICS",
            new string('-', 88),
            "Scope: " + Dist(rows, "feedback_scope"),
            "Sentiment: " + Dist(rows, "sentiment"),
            "Pain: " + Dist(rows, "pain_feedback"),
            "Actions: " + Dist(rows, "requested_action")
        };
        File.WriteAllLines(path, lines, Encoding.UTF8);
    }

    static string Dist(List<Dictionary<string, object>> rows, string col)
    {
        return string.Join("; ", rows.GroupBy(r => S(r, col)).OrderByDescending(g => g.Count()).Select(g => g.Key + "=" + g.Count()).ToArray());
    }

    static void PrintDist(string label, List<string> vals)
    {
        Console.WriteLine(label + "=" + string.Join("; ", vals.GroupBy(x => x).OrderByDescending(g => g.Count()).Select(g => g.Key + ":" + g.Count()).ToArray()));
    }

    static void WriteWorkbook(string path, List<Tuple<string, string[], List<Dictionary<string, object>>>> sheets)
    {
        if (File.Exists(path)) File.Delete(path);
        using (var fs = File.Open(path, FileMode.CreateNew))
        using (var zip = new ZipArchive(fs, ZipArchiveMode.Create))
        {
            WriteText(zip, "[Content_Types].xml", ContentTypes(sheets.Count));
            WriteText(zip, "_rels/.rels", "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/package/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/></Relationships>".Replace("http://schemas.openxmlformats.org/package/2006/relationships/officeDocument", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"));
            WriteText(zip, "xl/_rels/workbook.xml.rels", WorkbookRels(sheets.Count));
            WriteText(zip, "xl/workbook.xml", WorkbookXml(sheets.Select(s => s.Item1).ToList()));
            WriteText(zip, "xl/styles.xml", "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><styleSheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><fonts count=\"1\"><font><sz val=\"11\"/><name val=\"Calibri\"/></font></fonts><fills count=\"1\"><fill><patternFill patternType=\"none\"/></fill></fills><borders count=\"1\"><border/></borders><cellStyleXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\"/></cellStyleXfs><cellXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\" xfId=\"0\"/></cellXfs></styleSheet>");
            for (var i = 0; i < sheets.Count; i++) WriteSheet(zip, "xl/worksheets/sheet" + (i + 1) + ".xml", sheets[i].Item2, sheets[i].Item3);
        }
    }
    static void WriteSheet(ZipArchive zip, string entryName, string[] headers, List<Dictionary<string, object>> rows)
    {
        var entry = zip.CreateEntry(entryName, CompressionLevel.Optimal);
        using (var stream = entry.Open())
        using (var writer = XmlWriter.Create(stream, new XmlWriterSettings { Encoding = Encoding.UTF8, Indent = false }))
        {
            writer.WriteStartDocument(true); writer.WriteStartElement("worksheet", "http://schemas.openxmlformats.org/spreadsheetml/2006/main"); writer.WriteStartElement("sheetData");
            WriteRow(writer, 1, headers.Cast<object>().ToArray());
            for (var r = 0; r < rows.Count; r++) WriteRow(writer, r + 2, headers.Select(h => rows[r].ContainsKey(h) ? rows[r][h] : "").ToArray());
            writer.WriteEndElement(); writer.WriteEndElement(); writer.WriteEndDocument();
        }
    }
    static void WriteRow(XmlWriter writer, int rowNumber, object[] values)
    {
        writer.WriteStartElement("row"); writer.WriteAttributeString("r", rowNumber.ToString(CultureInfo.InvariantCulture));
        for (var c = 0; c < values.Length; c++)
        {
            var v = values[c]; if (v == null || v.ToString() == "") continue;
            writer.WriteStartElement("c"); writer.WriteAttributeString("r", ColName(c + 1) + rowNumber.ToString(CultureInfo.InvariantCulture));
            if (v is int || v is double || v is decimal) { writer.WriteStartElement("v"); writer.WriteString(Convert.ToString(v, CultureInfo.InvariantCulture)); writer.WriteEndElement(); }
            else { writer.WriteAttributeString("t", "inlineStr"); writer.WriteStartElement("is"); writer.WriteStartElement("t"); writer.WriteString(v.ToString()); writer.WriteEndElement(); writer.WriteEndElement(); }
            writer.WriteEndElement();
        }
        writer.WriteEndElement();
    }
    static string ContentTypes(int count) { var sb = new StringBuilder("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"><Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/><Default Extension=\"xml\" ContentType=\"application/xml\"/><Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/><Override PartName=\"/xl/styles.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml\"/>"); for (var i = 1; i <= count; i++) sb.Append("<Override PartName=\"/xl/worksheets/sheet" + i + ".xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/>"); return sb.Append("</Types>").ToString(); }
    static string WorkbookRels(int count) { var sb = new StringBuilder("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"); for (var i = 1; i <= count; i++) sb.Append("<Relationship Id=\"rId" + i + "\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet" + i + ".xml\"/>"); return sb.Append("<Relationship Id=\"rId" + (count + 1) + "\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles\" Target=\"styles.xml\"/></Relationships>").ToString(); }
    static string WorkbookXml(List<string> sheetNames) { var sb = new StringBuilder("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"><sheets>"); for (var i = 0; i < sheetNames.Count; i++) sb.Append("<sheet name=\"" + Escape(sheetNames[i]) + "\" sheetId=\"" + (i + 1) + "\" r:id=\"rId" + (i + 1) + "\"/>"); return sb.Append("</sheets></workbook>").ToString(); }
    static void WriteText(ZipArchive zip, string name, string text) { var entry = zip.CreateEntry(name, CompressionLevel.Optimal); using (var w = new StreamWriter(entry.Open(), new UTF8Encoding(false))) w.Write(text); }

    static List<Dictionary<string, string>> ReadSheet(string path, string sheetName)
    {
        using (var fs = File.Open(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
        using (var zip = new ZipArchive(fs, ZipArchiveMode.Read))
        {
            var shared = Shared(zip); var entryName = SheetEntry(zip, sheetName); var doc = XDocument.Load(zip.GetEntry(entryName).Open()); var headers = new Dictionary<string, string>(); var rows = new List<Dictionary<string, string>>();
            foreach (var row in doc.Descendants(Ns + "row"))
            {
                var rowNum = (int)row.Attribute("r");
                if (rowNum == 1) { foreach (var cell in row.Elements(Ns + "c")) headers[Col((string)cell.Attribute("r"))] = Text(cell, shared); continue; }
                var obj = new Dictionary<string, string> { { "_row", rowNum.ToString(CultureInfo.InvariantCulture) } };
                foreach (var cell in row.Elements(Ns + "c")) { var col = Col((string)cell.Attribute("r")); if (headers.ContainsKey(col)) obj[headers[col]] = Text(cell, shared); }
                if (obj.Count > 1) rows.Add(obj);
            }
            return rows;
        }
    }
    static string SheetEntry(ZipArchive zip, string sheetName) { var workbook = XDocument.Load(zip.GetEntry("xl/workbook.xml").Open()); var rels = XDocument.Load(zip.GetEntry("xl/_rels/workbook.xml.rels").Open()); var sheet = workbook.Descendants(Ns + "sheet").First(s => (string)s.Attribute("name") == sheetName); var rid = (string)sheet.Attribute(RelNs + "id"); var target = (string)rels.Descendants(PkgRelNs + "Relationship").First(r => (string)r.Attribute("Id") == rid).Attribute("Target"); target = target.TrimStart('/'); return target.StartsWith("xl/") ? target : "xl/" + target; }
    static List<string> Shared(ZipArchive zip) { var entry = zip.GetEntry("xl/sharedStrings.xml"); if (entry == null) return new List<string>(); var doc = XDocument.Load(entry.Open()); return doc.Descendants(Ns + "si").Select(si => string.Concat(si.Descendants(Ns + "t").Select(t => t.Value))).ToList(); }
    static string Text(XElement cell, List<string> shared) { var t = (string)cell.Attribute("t"); if (t == "s") { var idx = I(cell.Value); return idx >= 0 && idx < shared.Count ? shared[idx] : ""; } if (t == "inlineStr") return string.Concat(cell.Descendants(Ns + "t").Select(x => x.Value)); return cell.Value ?? ""; }
    static Dictionary<string, object> Row(string headerCsv, string valueCsv) { var h = headerCsv.Split(','); var v = valueCsv.Split(','); var r = new Dictionary<string, object>(); for (var i = 0; i < h.Length; i++) r[h[i]] = i < v.Length ? v[i] : ""; return r; }
    static string Json(IEnumerable<string> values) { return "[" + string.Join(",", values.Where(v => !string.IsNullOrWhiteSpace(v)).Distinct().Select(v => "\"" + v.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"").ToArray()) + "]"; }
    static string Col(string cellRef) { return Regex.Replace(cellRef ?? "", "\\d", ""); }
    static string ColName(int index) { var name = ""; while (index > 0) { var rem = (index - 1) % 26; name = (char)('A' + rem) + name; index = (index - 1) / 26; } return name; }
    static string Get(Dictionary<string, string> r, string k) { return r.ContainsKey(k) ? (r[k] ?? "").Trim() : ""; }
    static string S(Dictionary<string, object> r, string k) { return r.ContainsKey(k) && r[k] != null ? r[k].ToString() : ""; }
    static int I(string s) { int v; return int.TryParse((s ?? "").Split('.')[0], NumberStyles.Any, CultureInfo.InvariantCulture, out v) ? v : 0; }
    static double D(string s) { double v; return double.TryParse(s ?? "", NumberStyles.Any, CultureInfo.InvariantCulture, out v) ? v : 0.0; }
    static int Seed(string s) { unchecked { var h = 29; foreach (var c in s ?? "") h = h * 31 + c; return Math.Abs(h); } }
    static string Escape(string s) { return s.Replace("&", "&amp;").Replace("\"", "&quot;").Replace("<", "&lt;").Replace(">", "&gt;"); }
}
