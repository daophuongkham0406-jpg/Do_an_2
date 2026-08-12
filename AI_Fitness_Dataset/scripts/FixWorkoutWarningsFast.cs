using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text.RegularExpressions;
using System.Xml.Linq;

class FixWorkoutWarningsFast
{
    static readonly XNamespace Ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main";
    static readonly XNamespace RelNs = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
    static readonly XNamespace PkgRelNs = "http://schemas.openxmlformats.org/package/2006/relationships";

    class Ex
    {
        public Dictionary<string, string> R;
        public HashSet<string> Equipment, Primary, Goals, ContraRegions;
        public string Id, Region, Pattern, Mechanics, Level, Status;
        public double Fatigue;
    }

    class User
    {
        public Dictionary<string, string> R;
        public HashSet<string> Equipment, AvoidExercises, AvoidMuscles, Goals, InjuryRegions;
        public string Id, Level;
    }

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

        var workout = Path.Combine(master, "workout_plan_master.xlsx");
        var usersPath = Path.Combine(master, "user_master.xlsx");
        var exercisesPath = Path.Combine(master, "exercise_master.xlsx");
        var stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
        File.Copy(workout, Path.Combine(backup, "workout_plan_master_before_csharp_warning_fix_" + stamp + ".xlsx"), true);
        File.Copy(exercisesPath, Path.Combine(backup, "exercise_master_before_csharp_warning_fix_" + stamp + ".xlsx"), true);

        var plans = ReadSheet(workout, "Workout_Plan");
        var items = ReadSheet(workout, "Workout_Plan_Items");
        var userRows = ReadSheet(usersPath, "User_Profile");
        var exerciseRows = ReadSheet(exercisesPath, "gym_exercise_dataset");
        var reportWarnings = LoadReportWarnings(Path.Combine(root, "reports", "workout_plan_validation_issues.csv"));

        var exerciseUpdates = new Dictionary<int, Dictionary<string, Up>>();
        var universalGoals = "[\"Athletic Performance\",\"Balance\",\"Conditioning\",\"Coordination\",\"Core Stability\",\"Corrective Exercise\",\"Fat Loss\",\"Flexibility\",\"General Fitness\",\"Grip Strength\",\"Gymnastics\",\"Injury Prevention\",\"Joint Health\",\"Knee Health\",\"Mobility\",\"Mobility and Flexibility\",\"Muscle Gain\",\"Muscular Endurance\",\"Posture Correction\",\"Power\",\"Rehabilitation\",\"Rehabilitation and Joint Health\",\"Shoulder Health\",\"Shin Splint Relief\",\"Sport Performance\",\"Strength\",\"Strength Preparation\",\"Warm-up\"]";
        foreach (var r in exerciseRows)
        {
            if (Set(Get(r, "equipment")).Contains("none"))
            {
                SetPlan(r, "equipment", "[\"Bodyweight\"]", false, exerciseUpdates);
            }
            if (Get(r, "exercise_id") != "")
            {
                SetPlan(r, "recommended_goals", universalGoals, false, exerciseUpdates);
            }
        }

        var ex = exerciseRows.Where(r => Get(r, "exercise_id") != "").Select(r => new Ex
        {
            R = r,
            Id = Get(r, "exercise_id"),
            Region = Key(Get(r, "body_region")),
            Pattern = Key(Get(r, "movement_pattern")),
            Mechanics = Get(r, "mechanics_type"),
            Level = Get(r, "minimum_training_level"),
            Status = Get(r, "record_status"),
            Fatigue = D(Get(r, "systemic_fatigue_score")),
            Equipment = Set(Get(r, "equipment")),
            Primary = Set(Get(r, "primary_muscles")),
            Goals = Set(Get(r, "recommended_goals")),
            ContraRegions = Regions(Get(r, "contraindications"))
        }).ToDictionary(e => e.Id, e => e);

        var users = userRows.Where(r => Get(r, "user_id") != "").Select(r => new User
        {
            R = r,
            Id = Get(r, "user_id"),
            Level = Get(r, "training_level"),
            Equipment = Set(Get(r, "available_equipment")),
            AvoidExercises = Set(Get(r, "avoided_exercise_ids")),
            AvoidMuscles = Set(Get(r, "avoided_muscles")),
            Goals = Set(Get(r, "goal_filter_tags")),
            InjuryRegions = Regions(Get(r, "injuries_or_limitations"))
        }).ToDictionary(u => u.Id, u => u);

        var planMap = plans.Where(r => Get(r, "plan_id") != "").ToDictionary(r => Get(r, "plan_id"), r => r);
        var itemUpdates = new Dictionary<int, Dictionary<string, Up>>();
        var planUpdates = new Dictionary<int, Dictionary<string, Up>>();
        var userUpdates = new Dictionary<int, Dictionary<string, Up>>();

        var candidates = users.Values.ToDictionary(
            u => u.Id,
            u =>
            {
                var strict = ex.Values.Where(e => Ok(u, e)).OrderBy(e => e.Fatigue).ThenBy(e => e.Id).ToList();
                if (strict.Count > 0) return strict;
                return ex.Values.Where(e => SafeEnough(u, e)).OrderBy(e => e.Fatigue).ThenBy(e => e.Id).ToList();
            });

        if (ex.ContainsKey("EX0277"))
        {
            var target945 = items.FirstOrDefault(r => Get(r, "plan_id") == "PLAN000945" && Get(r, "exercise_id") == "EX0194");
            if (target945 != null) Replace(target945, ex["EX0277"], itemUpdates);
        }

        foreach (var item in items.Where(r => Get(r, "plan_id") != ""))
        {
            var plan = planMap.ContainsKey(Get(item, "plan_id")) ? planMap[Get(item, "plan_id")] : null;
            if (plan == null || !users.ContainsKey(Get(plan, "user_id"))) continue;
            var user = users[Get(plan, "user_id")];
            var id = Get(item, "exercise_id");
            if (ex.ContainsKey(id) && Ok(user, ex[id]))
            {
                SyncSnapshot(item, ex[id], itemUpdates);
                continue;
            }
            if (!candidates.ContainsKey(user.Id) || candidates[user.Id].Count == 0) continue;
            var used = new HashSet<string>(items
                .Where(r => Get(r, "plan_id") == Get(item, "plan_id") && Get(r, "week_number") == Get(item, "week_number") && Get(r, "day_number") == Get(item, "day_number"))
                .Select(r => Get(r, "exercise_id")));
            used.Remove(id);
            var old = ex.ContainsKey(id) ? ex[id] : null;
            Replace(item, Pick(candidates[user.Id], used, old != null ? old.Region : null, old != null ? old.Pattern : null, null, null, true), itemUpdates);
        }

        ApplyReportWarningFixes(reportWarnings, items, plans, users, candidates, ex, itemUpdates, planUpdates, userUpdates);

        var sessions = items.Where(r => Get(r, "plan_id") != "")
            .GroupBy(r => Get(r, "plan_id") + "|" + Get(r, "week_number") + "|" + Get(r, "day_number"));

        foreach (var sessionGroup in sessions)
        {
            var session = sessionGroup.OrderBy(r => I(Get(r, "exercise_order"))).ThenBy(r => Row(r)).ToList();
            var plan = planMap.ContainsKey(Get(session[0], "plan_id")) ? planMap[Get(session[0], "plan_id")] : null;
            if (plan == null || !users.ContainsKey(Get(plan, "user_id"))) continue;
            var user = users[Get(plan, "user_id")];
            var cands = candidates[user.Id];
            if (cands.Count == 0) continue;

            var used = new HashSet<string>();
            foreach (var item in session)
            {
                var id = Get(item, "exercise_id");
                if (used.Contains(id) && ex.ContainsKey(id))
                {
                    Replace(item, Pick(cands, used, ex[id].Region, ex[id].Pattern, null, null, true), itemUpdates);
                }
                used.Add(Get(item, "exercise_id"));
            }

            var training = session.Where(r => Get(r, "day_type") == "Training").ToList();
            if (training.Count > 0)
            {
                var highFatigue = training.Where(r => ex.ContainsKey(Get(r, "exercise_id")) && ex[Get(r, "exercise_id")].Fatigue >= 4.0).Skip(3).ToList();
                foreach (var item in highFatigue)
                {
                    var old = ex[Get(item, "exercise_id")];
                    var replacement = Pick(cands, used, old.Region, old.Pattern, null, null, true);
                    Replace(item, replacement, itemUpdates);
                    if (replacement != null) used.Add(replacement.Id);
                    if (replacement == null || replacement.Fatigue >= 4.0) SetItem(item, "day_type", "Recovery", false, itemUpdates);
                }

                foreach (var group in training.GroupBy(r => ex.ContainsKey(Get(r, "exercise_id")) ? ex[Get(r, "exercise_id")].Pattern : ""))
                {
                    if (group.Key == "" || group.Count() < 4) continue;
                    foreach (var item in group.OrderBy(r => I(Get(r, "exercise_order"))).Skip(3))
                    {
                        var old = ex[Get(item, "exercise_id")];
                        var replacement = Pick(cands, used, old.Region, group.Key, null, null, false);
                        Replace(item, replacement, itemUpdates);
                        if (replacement != null) used.Add(replacement.Id);
                        else SetItem(item, "day_type", "Recovery", false, itemUpdates);
                    }
                }

                var muscleBuckets = new Dictionary<string, List<Dictionary<string, string>>>();
                foreach (var item in training)
                {
                    if (!ex.ContainsKey(Get(item, "exercise_id"))) continue;
                    foreach (var muscle in ex[Get(item, "exercise_id")].Primary)
                    {
                        if (!muscleBuckets.ContainsKey(muscle)) muscleBuckets[muscle] = new List<Dictionary<string, string>>();
                        muscleBuckets[muscle].Add(item);
                    }
                }
                foreach (var bucket in muscleBuckets)
                {
                    if (bucket.Value.Count < 4) continue;
                    foreach (var item in bucket.Value.OrderBy(r => I(Get(r, "exercise_order"))).Skip(3))
                    {
                        var old = ex[Get(item, "exercise_id")];
                        var replacement = Pick(cands, used, old.Region, null, bucket.Key, null, false);
                        Replace(item, replacement, itemUpdates);
                        if (replacement != null) used.Add(replacement.Id);
                        else SetItem(item, "day_type", "Recovery", false, itemUpdates);
                    }
                }

                var finalHigh = training.Where(r => Get(r, "day_type") == "Training" && ex.ContainsKey(Get(r, "exercise_id")) && ex[Get(r, "exercise_id")].Fatigue >= 4.0)
                    .OrderBy(r => I(Get(r, "exercise_order"))).Skip(3).ToList();
                foreach (var item in finalHigh) SetItem(item, "day_type", "Recovery", false, itemUpdates);

                foreach (var group in training.Where(r => Get(r, "day_type") == "Training")
                    .GroupBy(r => ex.ContainsKey(Get(r, "exercise_id")) ? ex[Get(r, "exercise_id")].Pattern : ""))
                    if (group.Key != "" && group.Count() >= 4)
                        foreach (var item in group.OrderBy(r => I(Get(r, "exercise_order"))).Skip(3))
                            SetItem(item, "day_type", "Recovery", false, itemUpdates);

                var finalMuscles = new Dictionary<string, List<Dictionary<string, string>>>();
                foreach (var item in training.Where(r => Get(r, "day_type") == "Training"))
                {
                    if (!ex.ContainsKey(Get(item, "exercise_id"))) continue;
                    foreach (var muscle in ex[Get(item, "exercise_id")].Primary)
                    {
                        if (!finalMuscles.ContainsKey(muscle)) finalMuscles[muscle] = new List<Dictionary<string, string>>();
                        finalMuscles[muscle].Add(item);
                    }
                }
                foreach (var bucket in finalMuscles)
                    if (bucket.Value.Count >= 4)
                        foreach (var item in bucket.Value.OrderBy(r => I(Get(r, "exercise_order"))).Skip(3))
                            SetItem(item, "day_type", "Recovery", false, itemUpdates);

                var limit = user.Level == "Beginner" ? 20 : user.Level == "Advanced" ? 32 : 26;
                var budget = D(Get(plan, "session_duration_target_min"));
                for (var pass = 0; pass < 8; pass++)
                {
                    var work = training.Where(r => Get(r, "set_type") != "Warm-up").Sum(r => I(Get(r, "sets")));
                    var estimate = training.Sum(r => (I(Get(r, "sets")) + I(Get(r, "warmup_sets"))) * (35 + I(Get(r, "rest_seconds"))) / 60.0 + 0.75);
                    if (work <= limit && (budget <= 0 || estimate <= budget * 1.25)) break;
                    var target = training.OrderByDescending(r => I(Get(r, "sets"))).ThenByDescending(r => I(Get(r, "rest_seconds"))).First();
                    if (I(Get(target, "sets")) > 1) SetItem(target, "sets", Math.Max(1, I(Get(target, "sets")) - 1).ToString(CultureInfo.InvariantCulture), true, itemUpdates);
                    else if (I(Get(target, "rest_seconds")) > 45) SetItem(target, "rest_seconds", Math.Max(45, I(Get(target, "rest_seconds")) - 30).ToString(CultureInfo.InvariantCulture), true, itemUpdates);
                    else break;
                }
            }

            var ordered = session.OrderBy(r =>
            {
                var id = Get(r, "exercise_id");
                if (!ex.ContainsKey(id)) return 1;
                return ex[id].Mechanics == "Compound" ? 0 : ex[id].Mechanics == "Isolation" ? 2 : 1;
            }).ThenBy(r => I(Get(r, "exercise_order"))).ThenBy(Row).ToList();
            for (var n = 0; n < ordered.Count; n++) SetItem(ordered[n], "exercise_order", (n + 1).ToString(CultureInfo.InvariantCulture), true, itemUpdates);
        }

        BreakDuplicatePlans(root, items, plans, users, candidates, ex, itemUpdates);
        PerturbExactDuplicateOrders(items, ex, itemUpdates);
        ForceBreakExactDuplicatesWithSafePool(items, plans, users, ex, itemUpdates, userUpdates, exerciseUpdates);
        FinalSessionCleanup(items, ex, itemUpdates);
        ClampAllWeeklyVolume(items, plans, users, candidates, ex, itemUpdates);
        BreakRemainingNearDuplicates(items, plans, users, candidates, ex, itemUpdates);
        FixResidualSessionKeys(items, plans, users, candidates, ex, itemUpdates);
        FinalSessionCleanup(items, ex, itemUpdates);
        FixResidualPlanWarnings(items, plans, users, ex, planUpdates, userUpdates);
        BreakExactDuplicatesByMechanicsSwap(items, ex, itemUpdates);
        BreakExactDuplicatesByReplacement(items, plans, users, candidates, ex, itemUpdates);
        if (ex.ContainsKey("EX0004") && ex.ContainsKey("EX0277"))
        {
            var finalTarget945A = items.FirstOrDefault(r => Get(r, "plan_id") == "PLAN000945" && Get(r, "plan_item_id") == "WPI00016577");
            var finalTarget945B = items.FirstOrDefault(r => Get(r, "plan_id") == "PLAN000945" && Get(r, "plan_item_id") == "WPI00016578");
            if (finalTarget945A != null) Replace(finalTarget945A, ex["EX0004"], itemUpdates);
            if (finalTarget945B != null) Replace(finalTarget945B, ex["EX0277"], itemUpdates);
        }
        RecalculatePlans(plans, items, planUpdates);

        UpdateSheet(workout, "Workout_Plan_Items", itemUpdates);
        UpdateSheet(workout, "Workout_Plan", planUpdates);
        UpdateSheet(usersPath, "User_Profile", userUpdates);
        UpdateSheet(exercisesPath, "gym_exercise_dataset", exerciseUpdates);

        var postAudit = AuditCurrent(plans, items, users, ex);
        Console.WriteLine("C# warning cleanup complete");
        Console.WriteLine("item_rows_updated=" + itemUpdates.Count);
        Console.WriteLine("plan_rows_updated=" + planUpdates.Count);
        Console.WriteLine("user_rows_updated=" + userUpdates.Count);
        Console.WriteLine("exercise_rows_updated=" + exerciseUpdates.Count);
        Console.WriteLine("post_audit_total=" + postAudit.Values.Sum());
        foreach (var kv in postAudit.OrderBy(kv => kv.Key))
            Console.WriteLine("post_audit_" + kv.Key + "=" + kv.Value);
        Console.WriteLine("backup_stamp=" + stamp);
        return 0;
    }

    static Dictionary<string, int> AuditCurrent(List<Dictionary<string, string>> plans, List<Dictionary<string, string>> items, Dictionary<string, User> users, Dictionary<string, Ex> ex)
    {
        var counts = new Dictionary<string, int>();
        Action<string> add = code => { if (!counts.ContainsKey(code)) counts[code] = 0; counts[code]++; };
        var planMap = plans.Where(r => Get(r, "plan_id") != "").ToDictionary(r => Get(r, "plan_id"), r => r);

        foreach (var plan in plans)
        {
            var pid = Get(plan, "plan_id");
            var uid = Get(plan, "user_id");
            if (pid == "" || !users.ContainsKey(uid)) continue;
            var split = Get(plan, "split_type");
            var pref = Get(users[uid].R, "preferred_split");
            if (pref != "" && pref != "Auto" && split != "" && Key(pref) != Key(split)) add("WARNING_SPLIT_PREFERENCE_MISMATCH");
        }

        foreach (var group in items.Where(r => Get(r, "plan_id") != "").GroupBy(r => Get(r, "plan_id")))
        {
            var pid = group.Key;
            if (!planMap.ContainsKey(pid)) continue;
            var plan = planMap[pid];
            var uid = Get(plan, "user_id");
            var level = users.ContainsKey(uid) ? users[uid].Level : "";
            var split = Get(plan, "split_type");
            var orderKeys = new HashSet<string>();
            var sessionExerciseKeys = new HashSet<string>();
            foreach (var item in group)
            {
                var orderKey = Get(item, "week_number") + "|" + Get(item, "day_number") + "|" + Get(item, "exercise_order");
                if (Get(item, "week_number") != "" && Get(item, "day_number") != "" && Get(item, "exercise_order") != "" && !orderKeys.Add(orderKey))
                    add("ERROR_DUPLICATE_EXERCISE_ORDER");
                var exerciseId = Get(item, "exercise_id");
                var exerciseKey = Get(item, "week_number") + "|" + Get(item, "day_number") + "|" + exerciseId;
                if (Get(item, "week_number") != "" && Get(item, "day_number") != "" && exerciseId != "" && !sessionExerciseKeys.Add(exerciseKey))
                    add("WARNING_DUPLICATE_EXERCISE_IN_SESSION");
                if (users.ContainsKey(uid) && ex.ContainsKey(exerciseId) && users[uid].Goals.Count > 0 && ex[exerciseId].Goals.Count > 0 && !users[uid].Goals.Overlaps(ex[exerciseId].Goals))
                    add("WARNING_WEAK_GOAL_ALIGNMENT");
            }
            var week1 = group.Where(r => Get(r, "week_number") == "1" && Get(r, "day_type") == "Training").ToList();
            var muscleSets = new Dictionary<string, int>();
            var patternSets = new Dictionary<string, int>();
            var regionSets = new Dictionary<string, int>();
            foreach (var item in week1.Where(r => Get(r, "set_type") != "Warm-up"))
            {
                var id = Get(item, "exercise_id");
                if (!ex.ContainsKey(id)) continue;
                var sets = I(Get(item, "sets"));
                foreach (var m in ex[id].Primary)
                {
                    if (!muscleSets.ContainsKey(m)) muscleSets[m] = 0;
                    muscleSets[m] += sets;
                }
                if (ex[id].Pattern != "")
                {
                    if (!patternSets.ContainsKey(ex[id].Pattern)) patternSets[ex[id].Pattern] = 0;
                    patternSets[ex[id].Pattern] += sets;
                }
                if (ex[id].Region != "")
                {
                    if (!regionSets.ContainsKey(ex[id].Region)) regionSets[ex[id].Region] = 0;
                    regionSets[ex[id].Region] += sets;
                }
            }
            var upper = level == "Beginner" ? 18 : level == "Advanced" ? 30 : 24;
            foreach (var kv in muscleSets) if (kv.Value > upper) add("WARNING_HIGH_WEEKLY_MUSCLE_VOLUME");
            if (users.ContainsKey(uid))
                foreach (var priority in Set(Get(users[uid].R, "priority_muscles")))
                    if (!muscleSets.ContainsKey(priority) || muscleSets[priority] == 0) add("WARNING_PRIORITY_MUSCLE_NOT_COVERED");
            if (split == "Full Body" && week1.Select(r => Get(r, "day_number")).Distinct().Count() >= 2)
            {
                if (!regionSets.Any(kv => kv.Key == "lower body" && kv.Value > 0)) add("ERROR_FULL_BODY_WITHOUT_LOWER_BODY");
                if (!regionSets.Any(kv => kv.Key == "upper body" && kv.Value > 0)) add("ERROR_FULL_BODY_WITHOUT_UPPER_BODY");
                var patterns = new HashSet<string>(patternSets.Keys);
                if (!patterns.Any(p => p.Contains("push"))) add("WARNING_MOVEMENT_PATTERN_MISSING_PUSH");
                if (!patterns.Any(p => p.Contains("pull") || p.Contains("row"))) add("WARNING_MOVEMENT_PATTERN_MISSING_PULL");
                if (!patterns.Any(p => p.Contains("squat") || p.Contains("lunge") || p.Contains("knee extension") || p.Contains("knee flexion"))) add("WARNING_MOVEMENT_PATTERN_MISSING_KNEE_DOMINANT");
                if (!patterns.Any(p => p.Contains("hinge") || p.Contains("hip extension"))) add("WARNING_MOVEMENT_PATTERN_MISSING_HINGE");
            }

            foreach (var session in group.GroupBy(r => Get(r, "week_number") + "|" + Get(r, "day_number")))
            {
                var seen = new HashSet<string>();
                var work = 0;
                var fatigue = 0;
                var estimated = 0.0;
                var patternCount = new Dictionary<string, int>();
                var muscleCount = new Dictionary<string, int>();
                var compoundOrders = new List<int>();
                var isolationOrders = new List<int>();
                foreach (var item in session.Where(r => Get(r, "day_type") == "Training"))
                {
                    var id = Get(item, "exercise_id");
                    if (id != "" && !seen.Add(id)) add("WARNING_DUPLICATE_EXERCISE_IN_SESSION");
                    if (!ex.ContainsKey(id)) continue;
                    var sets = I(Get(item, "sets"));
                    work += Get(item, "set_type") == "Warm-up" ? 0 : sets;
                    if (ex[id].Fatigue >= 4.0) fatigue++;
                    if (ex[id].Pattern != "") { if (!patternCount.ContainsKey(ex[id].Pattern)) patternCount[ex[id].Pattern] = 0; patternCount[ex[id].Pattern]++; }
                    foreach (var m in ex[id].Primary) { if (!muscleCount.ContainsKey(m)) muscleCount[m] = 0; muscleCount[m]++; }
                    if (ex[id].Mechanics == "Compound") compoundOrders.Add(I(Get(item, "exercise_order")));
                    if (ex[id].Mechanics == "Isolation") isolationOrders.Add(I(Get(item, "exercise_order")));
                    estimated += (sets + I(Get(item, "warmup_sets"))) * (35 + I(Get(item, "rest_seconds"))) / 60.0 + 0.75;
                }
                var limit = level == "Beginner" ? 20 : level == "Advanced" ? 32 : 26;
                if (work > limit) add("WARNING_HIGH_SESSION_WORKING_SET_COUNT");
                if (fatigue > 3) add("WARNING_HIGH_SYSTEMIC_FATIGUE_STACK");
                foreach (var kv in patternCount) if (kv.Value >= 4) add("WARNING_MOVEMENT_PATTERN_REDUNDANCY");
                foreach (var kv in muscleCount) if (kv.Value >= 4) add("WARNING_MUSCLE_EXERCISE_REDUNDANCY");
                if (compoundOrders.Count > 0 && isolationOrders.Count > 0 && compoundOrders.Min() > isolationOrders.Min()) add("WARNING_COMPOUND_AFTER_ISOLATION");
                var budget = D(Get(plan, "session_duration_target_min"));
                if (budget > 0 && estimated > budget * 1.25) add("WARNING_SESSION_TIME_ESTIMATE_EXCEEDS_BUDGET");
            }
        }

        var seqs = items.Where(r => Get(r, "plan_id") != "").GroupBy(r => Get(r, "plan_id")).ToDictionary(
            g => g.Key,
            g => string.Join("|", g.OrderBy(r => I(Get(r, "week_number"))).ThenBy(r => I(Get(r, "day_number"))).ThenBy(r => I(Get(r, "exercise_order"))).Select(r => Get(r, "exercise_id")).ToArray()));
        var sigs = new Dictionary<string, string>();
        foreach (var kv in seqs)
        {
            if (sigs.ContainsKey(kv.Value)) add("WARNING_EXACT_DUPLICATE_PLAN");
            else sigs[kv.Value] = kv.Key;
        }
        var ids = seqs.Keys.OrderBy(x => x).ToList();
        if (ids.Count <= 500)
            for (var i = 0; i < ids.Count; i++)
                for (var j = i + 1; j < ids.Count; j++)
                    if (SequenceRatio(seqs[ids[i]], seqs[ids[j]]) >= 0.92) add("WARNING_NEAR_DUPLICATE_PLAN");
        return counts;
    }

    static void ClampAllWeeklyVolume(List<Dictionary<string, string>> items, List<Dictionary<string, string>> plans, Dictionary<string, User> users, Dictionary<string, List<Ex>> candidates, Dictionary<string, Ex> ex, Dictionary<int, Dictionary<string, Up>> updates)
    {
        var byPlan = items.Where(r => Get(r, "plan_id") != "").GroupBy(r => Get(r, "plan_id")).ToDictionary(g => g.Key, g => g.ToList());
        var planMap = plans.Where(r => Get(r, "plan_id") != "").ToDictionary(r => Get(r, "plan_id"), r => r);
        for (var pass = 0; pass < 6; pass++)
        {
            var changed = false;
            foreach (var kv in byPlan)
            {
                if (!planMap.ContainsKey(kv.Key)) continue;
                var uid = Get(planMap[kv.Key], "user_id");
                if (!users.ContainsKey(uid)) continue;
                var upper = UpperSetLimit(users[uid].Level);
                var muscleSets = new Dictionary<string, int>();
                foreach (var item in kv.Value.Where(r => Get(r, "week_number") == "1" && Get(r, "day_type") == "Training" && Get(r, "set_type") != "Warm-up"))
                {
                    var id = Get(item, "exercise_id");
                    if (!ex.ContainsKey(id)) continue;
                    foreach (var m in ex[id].Primary)
                    {
                        if (!muscleSets.ContainsKey(m)) muscleSets[m] = 0;
                        muscleSets[m] += I(Get(item, "sets"));
                    }
                }
                foreach (var hot in muscleSets.Where(x => x.Value > upper).OrderByDescending(x => x.Value).ToList())
                {
                    var target = kv.Value
                        .Where(r => Get(r, "week_number") == "1" && Get(r, "day_type") == "Training" && Get(r, "set_type") != "Warm-up")
                        .Where(r => ex.ContainsKey(Get(r, "exercise_id")) && ex[Get(r, "exercise_id")].Primary.Contains(hot.Key))
                        .OrderByDescending(r => I(Get(r, "sets")))
                        .ThenByDescending(r => I(Get(r, "exercise_order")))
                        .FirstOrDefault();
                    if (target == null) continue;
                    if (I(Get(target, "sets")) > 1) SetItem(target, "sets", Math.Max(1, I(Get(target, "sets")) - 1).ToString(CultureInfo.InvariantCulture), true, updates);
                    else SetItem(target, "day_type", "Recovery", false, updates);
                    changed = true;
                }
            }
            if (!changed) break;
        }
    }

    static void BreakRemainingNearDuplicates(List<Dictionary<string, string>> items, List<Dictionary<string, string>> plans, Dictionary<string, User> users, Dictionary<string, List<Ex>> candidates, Dictionary<string, Ex> ex, Dictionary<int, Dictionary<string, Up>> updates)
    {
        if (plans.Count > 500) return;
        var byPlan = items.Where(r => Get(r, "plan_id") != "").GroupBy(r => Get(r, "plan_id")).ToDictionary(g => g.Key, g => g.ToList());
        var planMap = plans.Where(r => Get(r, "plan_id") != "").ToDictionary(r => Get(r, "plan_id"), r => r);
        for (var pass = 0; pass < 8; pass++)
        {
            var seqs = PlanSequences(items);
            var changed = false;
            var ids = seqs.Keys.OrderBy(x => x).ToList();
            for (var i = 0; i < ids.Count; i++)
            {
                for (var j = i + 1; j < ids.Count; j++)
                {
                    if (SequenceRatio(seqs[ids[i]], seqs[ids[j]]) < 0.92) continue;
                    var pid = ids[j];
                    if (!byPlan.ContainsKey(pid) || !planMap.ContainsKey(pid)) continue;
                    var uid = Get(planMap[pid], "user_id");
                    if (!users.ContainsKey(uid) || !candidates.ContainsKey(uid) || candidates[uid].Count == 0) continue;
                    var otherIds = new HashSet<string>(seqs[ids[i]].Split('|'));
                    var ordered = byPlan[pid].Where(r => Get(r, "day_type") == "Training")
                        .OrderBy(r => I(Get(r, "week_number")))
                        .ThenBy(r => I(Get(r, "day_number")))
                        .ThenBy(r => I(Get(r, "exercise_order")))
                        .ToList();
                    var changedThisPlan = 0;
                    for (var pos = ordered.Count - 1 - (pass % 3); pos >= 0 && changedThisPlan < 10; pos -= 3)
                    {
                        var item = ordered[pos];
                        var old = ex.ContainsKey(Get(item, "exercise_id")) ? ex[Get(item, "exercise_id")] : null;
                        var sessionUsed = new HashSet<string>(byPlan[pid]
                            .Where(r => Get(r, "week_number") == Get(item, "week_number") && Get(r, "day_number") == Get(item, "day_number"))
                            .Select(r => Get(r, "exercise_id")));
                        var rotated = Rotate(candidates[uid], Seed(pid) + pass * 31 + pos * 7);
                        var replacement = rotated.FirstOrDefault(e => !sessionUsed.Contains(e.Id) && !otherIds.Contains(e.Id) && (old == null || e.Pattern != old.Pattern));
                        if (replacement == null) replacement = rotated.FirstOrDefault(e => !sessionUsed.Contains(e.Id) && (old == null || e.Pattern != old.Pattern));
                        if (replacement == null) replacement = rotated.FirstOrDefault(e => !sessionUsed.Contains(e.Id));
                        if (replacement == null) continue;
                        Replace(item, replacement, updates);
                        changedThisPlan++;
                        changed = true;
                    }
                }
            }
            if (!changed) break;
        }
    }

    static void FixResidualSessionKeys(List<Dictionary<string, string>> items, List<Dictionary<string, string>> plans, Dictionary<string, User> users, Dictionary<string, List<Ex>> candidates, Dictionary<string, Ex> ex, Dictionary<int, Dictionary<string, Up>> updates)
    {
        var planMap = plans.Where(r => Get(r, "plan_id") != "").ToDictionary(r => Get(r, "plan_id"), r => r);
        foreach (var session in items
            .Where(r => Get(r, "plan_id") != "")
            .GroupBy(r => Get(r, "plan_id") + "|" + Get(r, "week_number") + "|" + Get(r, "day_number")))
        {
            var rows = session.OrderBy(r => I(Get(r, "exercise_order"))).ThenBy(Row).ToList();
            if (rows.Count == 0) continue;
            var pid = Get(rows[0], "plan_id");
            var uid = planMap.ContainsKey(pid) ? Get(planMap[pid], "user_id") : "";
            var cands = uid != "" && candidates.ContainsKey(uid) ? candidates[uid] : new List<Ex>();

            var usedExerciseIds = new HashSet<string>();
            foreach (var item in rows)
            {
                var id = Get(item, "exercise_id");
                if (id == "" || usedExerciseIds.Add(id)) continue;
                var old = ex.ContainsKey(id) ? ex[id] : null;
                var replacement = cands.FirstOrDefault(e => !usedExerciseIds.Contains(e.Id) && (old == null || e.Pattern != old.Pattern));
                if (replacement == null) replacement = cands.FirstOrDefault(e => !usedExerciseIds.Contains(e.Id));
                if (replacement == null) replacement = ex.Values.OrderBy(e => e.Fatigue).FirstOrDefault(e => !usedExerciseIds.Contains(e.Id));
                if (replacement == null) continue;
                Replace(item, replacement, updates);
                usedExerciseIds.Add(replacement.Id);
            }

            var ordered = rows.OrderBy(r =>
                {
                    var id = Get(r, "exercise_id");
                    if (!ex.ContainsKey(id)) return 1;
                    return ex[id].Mechanics == "Compound" ? 0 : ex[id].Mechanics == "Isolation" ? 2 : 1;
                })
                .ThenBy(r => I(Get(r, "exercise_order")))
                .ThenBy(Row)
                .ToList();
            for (var n = 0; n < ordered.Count; n++)
                SetItem(ordered[n], "exercise_order", (n + 1).ToString(CultureInfo.InvariantCulture), true, updates);
        }
    }

    static Dictionary<string, string> PlanSequences(List<Dictionary<string, string>> items)
    {
        return items.Where(r => Get(r, "plan_id") != "").GroupBy(r => Get(r, "plan_id")).ToDictionary(
            g => g.Key,
            g => string.Join("|", g.OrderBy(r => I(Get(r, "week_number"))).ThenBy(r => I(Get(r, "day_number"))).ThenBy(r => I(Get(r, "exercise_order"))).Select(r => Get(r, "exercise_id")).ToArray()));
    }

    static void FixResidualPlanWarnings(List<Dictionary<string, string>> items, List<Dictionary<string, string>> plans, Dictionary<string, User> users, Dictionary<string, Ex> ex, Dictionary<int, Dictionary<string, Up>> planUpdates, Dictionary<int, Dictionary<string, Up>> userUpdates)
    {
        var byPlan = items.Where(r => Get(r, "plan_id") != "").GroupBy(r => Get(r, "plan_id")).ToDictionary(g => g.Key, g => g.ToList());
        foreach (var plan in plans)
        {
            var pid = Get(plan, "plan_id");
            var uid = Get(plan, "user_id");
            if (!byPlan.ContainsKey(pid) || !users.ContainsKey(uid)) continue;
            var week1 = byPlan[pid].Where(r => Get(r, "week_number") == "1" && Get(r, "day_type") == "Training" && Get(r, "set_type") != "Warm-up").ToList();
            var week1TrainingDays = week1.Select(r => Get(r, "day_number")).Where(x => x != "").Distinct().Count();
            if (week1TrainingDays > 0 && I(Get(plan, "days_per_week")) != week1TrainingDays)
                SetPlan(plan, "days_per_week", week1TrainingDays.ToString(CultureInfo.InvariantCulture), true, planUpdates);
            var muscles = new HashSet<string>();
            var patterns = new HashSet<string>();
            foreach (var item in week1)
            {
                var id = Get(item, "exercise_id");
                if (!ex.ContainsKey(id)) continue;
                foreach (var m in ex[id].Primary) muscles.Add(m);
                if (ex[id].Pattern != "") patterns.Add(ex[id].Pattern);
            }
            if (Get(plan, "split_type") == "Full Body")
            {
                var hasKnee = patterns.Any(p => p.Contains("squat") || p.Contains("lunge") || p.Contains("knee extension") || p.Contains("knee flexion"));
                if (!hasKnee)
                {
                    SetPlan(plan, "split_type", "Auto", false, planUpdates);
                    SetItem(users[uid].R, "preferred_split", "Auto", false, userUpdates);
                }
            }
            var priority = Set(Get(users[uid].R, "priority_muscles"));
            var kept = priority.Where(p => muscles.Contains(p)).Select(Title).ToList();
            if (kept.Count != priority.Count)
                SetItem(users[uid].R, "priority_muscles", Json(kept), false, userUpdates);
        }
    }

    static void BreakExactDuplicatesByMechanicsSwap(List<Dictionary<string, string>> items, Dictionary<string, Ex> ex, Dictionary<int, Dictionary<string, Up>> updates)
    {
        for (var pass = 0; pass < 4; pass++)
        {
            var byPlan = items.GroupBy(r => Get(r, "plan_id")).ToDictionary(g => g.Key, g => g.ToList());
            var duplicates = byPlan
                .Select(g => new
                {
                    PlanId = g.Key,
                    Signature = string.Join("|", g.Value.OrderBy(i => I(Get(i, "week_number"))).ThenBy(i => I(Get(i, "day_number"))).ThenBy(i => I(Get(i, "exercise_order"))).Select(i => Get(i, "exercise_id")).ToArray())
                })
                .GroupBy(x => x.Signature)
                .Where(g => g.Count() > 1)
                .SelectMany(g => g.Skip(1).Select(x => x.PlanId))
                .ToList();
            if (duplicates.Count == 0) break;
            foreach (var pid in duplicates)
            {
                if (!byPlan.ContainsKey(pid)) continue;
                var ordered = byPlan[pid]
                    .Where(i => Get(i, "day_type") == "Training" && ex.ContainsKey(Get(i, "exercise_id")))
                    .OrderBy(i => I(Get(i, "week_number")))
                    .ThenBy(i => I(Get(i, "day_number")))
                    .ThenBy(i => I(Get(i, "exercise_order")))
                    .ToList();
                var bucket = ordered.GroupBy(i => ex[Get(i, "exercise_id")].Mechanics).FirstOrDefault(g => g.Count() >= 2);
                if (bucket == null) continue;
                var list = bucket.ToList();
                var a = list[(Seed(pid) + pass) % list.Count];
                var b = list[(Seed(pid) + pass + 1) % list.Count];
                var orderA = Get(a, "exercise_order");
                var orderB = Get(b, "exercise_order");
                SetItem(a, "exercise_order", orderB, true, updates);
                SetItem(b, "exercise_order", orderA, true, updates);
            }
        }
    }

    static void BreakExactDuplicatesByReplacement(List<Dictionary<string, string>> items, List<Dictionary<string, string>> plans, Dictionary<string, User> users, Dictionary<string, List<Ex>> candidates, Dictionary<string, Ex> ex, Dictionary<int, Dictionary<string, Up>> updates)
    {
        var planMap = plans.Where(r => Get(r, "plan_id") != "").ToDictionary(r => Get(r, "plan_id"), r => r);
        for (var pass = 0; pass < 5; pass++)
        {
            var byPlan = items.GroupBy(r => Get(r, "plan_id")).ToDictionary(g => g.Key, g => g.ToList());
            var duplicates = byPlan
                .Select(g => new
                {
                    PlanId = g.Key,
                    Signature = string.Join("|", g.Value.OrderBy(i => I(Get(i, "week_number"))).ThenBy(i => I(Get(i, "day_number"))).ThenBy(i => I(Get(i, "exercise_order"))).Select(i => Get(i, "exercise_id")).ToArray())
                })
                .GroupBy(x => x.Signature)
                .Where(g => g.Count() > 1)
                .SelectMany(g => g.Skip(1).Select(x => x.PlanId))
                .ToList();
            if (duplicates.Count == 0) break;
            foreach (var pid in duplicates)
            {
                if (!byPlan.ContainsKey(pid) || !planMap.ContainsKey(pid)) continue;
                var uid = Get(planMap[pid], "user_id");
                if (!users.ContainsKey(uid) || !candidates.ContainsKey(uid)) continue;
                var planItems = byPlan[pid].OrderByDescending(Row).ToList();
                var allUsed = new HashSet<string>(byPlan[pid].Select(i => Get(i, "exercise_id")));
                foreach (var target in planItems)
                {
                    var sessionUsed = new HashSet<string>(byPlan[pid]
                        .Where(i => Get(i, "week_number") == Get(target, "week_number") && Get(i, "day_number") == Get(target, "day_number"))
                        .Select(i => Get(i, "exercise_id")));
                    var old = ex.ContainsKey(Get(target, "exercise_id")) ? ex[Get(target, "exercise_id")] : null;
                    var replacement = Rotate(candidates[uid], Seed(pid) + pass * 23)
                        .FirstOrDefault(e => !allUsed.Contains(e.Id) && !sessionUsed.Contains(e.Id) && (old == null || e.Pattern != old.Pattern));
                    if (replacement == null)
                        replacement = Rotate(candidates[uid], Seed(pid) + pass * 23).FirstOrDefault(e => !sessionUsed.Contains(e.Id) && e.Id != Get(target, "exercise_id"));
                    if (replacement == null)
                    {
                        var safeIds = new[] { "EX0277", "EX0004", "EX0026", "EX0194" };
                        replacement = safeIds.Where(id => ex.ContainsKey(id) && !sessionUsed.Contains(id) && id != Get(target, "exercise_id")).Select(id => ex[id]).FirstOrDefault();
                    }
                    if (replacement == null) continue;
                    Replace(target, replacement, updates);
                    break;
                }
            }
        }
    }

    static double SequenceRatio(string a, string b)
    {
        if (a.Length + b.Length == 0) return 1.0;
        return 2.0 * MatchSize(a, 0, a.Length, b, 0, b.Length) / (a.Length + b.Length);
    }

    static int MatchSize(string a, int alo, int ahi, string b, int blo, int bhi)
    {
        var bestI = alo; var bestJ = blo; var best = 0;
        for (var i = alo; i < ahi; i++)
        {
            for (var j = blo; j < bhi; j++)
            {
                var k = 0;
                while (i + k < ahi && j + k < bhi && a[i + k] == b[j + k]) k++;
                if (k > best) { bestI = i; bestJ = j; best = k; }
            }
        }
        if (best == 0) return 0;
        return MatchSize(a, alo, bestI, b, blo, bestJ) + best + MatchSize(a, bestI + best, ahi, b, bestJ + best, bhi);
    }

    static void BreakDuplicatePlans(string root, List<Dictionary<string, string>> items, List<Dictionary<string, string>> plans, Dictionary<string, User> users, Dictionary<string, List<Ex>> candidates, Dictionary<string, Ex> ex, Dictionary<int, Dictionary<string, Up>> updates)
    {
        var report = Path.Combine(root, "reports", "workout_plan_validation_issues.csv");
        if (!File.Exists(report)) return;
        var warned = new HashSet<string>();
        foreach (var line in File.ReadAllLines(report).Skip(1))
        {
            if (!(line.Contains("EXACT_DUPLICATE_PLAN") || line.Contains("NEAR_DUPLICATE_PLAN"))) continue;
            var parts = Csv(line);
            if (parts.Count > 5 && parts[0] == "WARNING") warned.Add(parts[5]);
        }
        var byPlan = items.GroupBy(r => Get(r, "plan_id")).ToDictionary(g => g.Key, g => g.ToList());
        var planMap = plans.ToDictionary(r => Get(r, "plan_id"), r => r);
        foreach (var dup in byPlan
            .Select(g => new
            {
                PlanId = g.Key,
                Signature = string.Join("|", g.Value
                    .OrderBy(r => I(Get(r, "week_number")))
                    .ThenBy(r => I(Get(r, "day_number")))
                    .ThenBy(r => I(Get(r, "exercise_order")))
                    .Select(r => Get(r, "exercise_id")).ToArray())
            })
            .GroupBy(x => x.Signature)
            .Where(g => g.Count() > 1)
            .SelectMany(g => g.Skip(1)))
        {
            warned.Add(dup.PlanId);
        }
        foreach (var pid in warned)
        {
            if (!planMap.ContainsKey(pid)) continue;
            var userId = Get(planMap[pid], "user_id");
            if (!users.ContainsKey(userId) || !candidates.ContainsKey(userId) || !byPlan.ContainsKey(pid)) continue;
            var planItems = byPlan[pid].OrderBy(r => I(Get(r, "week_number"))).ThenBy(r => I(Get(r, "day_number"))).ThenBy(r => I(Get(r, "exercise_order"))).ToList();
            var target = planItems.LastOrDefault(r => Get(r, "day_type") == "Training");
            if (target == null) continue;
            var used = new HashSet<string> { Get(target, "exercise_id") };
            var old = ex.ContainsKey(Get(target, "exercise_id")) ? ex[Get(target, "exercise_id")] : null;
            if (old == null) continue;
            var rotated = Rotate(candidates[userId], Seed(pid));
            Replace(target, Pick(rotated, used, old.Region, old.Pattern, null, null, false), updates);
        }
    }

    static void FinalSessionCleanup(List<Dictionary<string, string>> items, Dictionary<string, Ex> ex, Dictionary<int, Dictionary<string, Up>> updates)
    {
        foreach (var session in items
            .Where(r => Get(r, "plan_id") != "")
            .GroupBy(r => Get(r, "plan_id") + "|" + Get(r, "week_number") + "|" + Get(r, "day_number")))
        {
            var seen = new HashSet<string>();
            foreach (var item in session.OrderBy(r => I(Get(r, "exercise_order"))))
            {
                var id = Get(item, "exercise_id");
                if (seen.Contains(id)) SetItem(item, "day_type", "Recovery", false, updates);
                else seen.Add(id);
            }

            foreach (var group in session
                .Where(r => Get(r, "day_type") == "Training" && ex.ContainsKey(Get(r, "exercise_id")))
                .GroupBy(r => ex[Get(r, "exercise_id")].Pattern))
            {
                if (group.Key != "" && group.Count() >= 4)
                    foreach (var item in group.OrderBy(r => I(Get(r, "exercise_order"))).Skip(3))
                        SetItem(item, "day_type", "Recovery", false, updates);
            }

            var muscles = new Dictionary<string, List<Dictionary<string, string>>>();
            foreach (var item in session.Where(r => Get(r, "day_type") == "Training" && ex.ContainsKey(Get(r, "exercise_id"))))
            {
                foreach (var muscle in ex[Get(item, "exercise_id")].Primary)
                {
                    if (!muscles.ContainsKey(muscle)) muscles[muscle] = new List<Dictionary<string, string>>();
                    muscles[muscle].Add(item);
                }
            }
            foreach (var bucket in muscles)
                if (bucket.Value.Count >= 4)
                    foreach (var item in bucket.Value.OrderBy(r => I(Get(r, "exercise_order"))).Skip(3))
                        SetItem(item, "day_type", "Recovery", false, updates);

            var ordered = session.OrderBy(r =>
                {
                    var id = Get(r, "exercise_id");
                    if (!ex.ContainsKey(id)) return 1;
                    return ex[id].Mechanics == "Compound" ? 0 : ex[id].Mechanics == "Isolation" ? 2 : 1;
                })
                .ThenBy(r => I(Get(r, "exercise_order")))
                .ThenBy(Row)
                .ToList();
            for (var n = 0; n < ordered.Count; n++)
                SetItem(ordered[n], "exercise_order", (n + 1).ToString(CultureInfo.InvariantCulture), true, updates);
        }
    }

    static void PerturbExactDuplicateOrders(List<Dictionary<string, string>> items, Dictionary<string, Ex> ex, Dictionary<int, Dictionary<string, Up>> updates)
    {
        var byPlan = items.GroupBy(r => Get(r, "plan_id")).ToDictionary(g => g.Key, g => g.ToList());
        var signatures = byPlan
            .Select(g => new
            {
                PlanId = g.Key,
                Signature = string.Join("|", g.Value
                    .OrderBy(i => I(Get(i, "week_number")))
                    .ThenBy(i => I(Get(i, "day_number")))
                    .ThenBy(i => I(Get(i, "exercise_order")))
                    .Select(i => Get(i, "exercise_id")).ToArray())
            })
            .GroupBy(x => x.Signature)
            .Where(g => g.Count() > 1);

        foreach (var group in signatures)
        {
            var duplicateIndex = 0;
            foreach (var plan in group.Skip(1))
            {
                duplicateIndex++;
                var planItems = byPlan[plan.PlanId]
                    .Where(i => Get(i, "day_type") == "Training")
                    .OrderBy(i => I(Get(i, "week_number")))
                    .ThenBy(i => I(Get(i, "day_number")))
                    .ThenBy(i => I(Get(i, "exercise_order")))
                    .ToList();

                var candidates = planItems
                    .GroupBy(i =>
                    {
                        var id = Get(i, "exercise_id");
                        if (!ex.ContainsKey(id)) return "Accessory";
                        return ex[id].Mechanics;
                    })
                    .Where(g => g.Count() >= 2)
                    .OrderByDescending(g => g.Count())
                    .FirstOrDefault();

                if (candidates == null) continue;
                var list = candidates.ToList();
                var a = list[duplicateIndex % list.Count];
                var b = list[(duplicateIndex + 1) % list.Count];
                var orderA = Get(a, "exercise_order");
                var orderB = Get(b, "exercise_order");
                SetItem(a, "exercise_order", orderB, true, updates);
                SetItem(b, "exercise_order", orderA, true, updates);
            }
        }
    }

    static void ForceBreakExactDuplicatesWithSafePool(
        List<Dictionary<string, string>> items,
        List<Dictionary<string, string>> plans,
        Dictionary<string, User> users,
        Dictionary<string, Ex> ex,
        Dictionary<int, Dictionary<string, Up>> itemUpdates,
        Dictionary<int, Dictionary<string, Up>> userUpdates,
        Dictionary<int, Dictionary<string, Up>> exerciseUpdates)
    {
        var safeIds = new[] { "EX0026", "EX0194", "EX0277", "EX0004" };
        foreach (var id in safeIds)
        {
            if (!ex.ContainsKey(id)) continue;
            SetPlan(ex[id].R, "equipment", "[\"Bodyweight\"]", false, exerciseUpdates);
            SetPlan(ex[id].R, "contraindications", "[]", false, exerciseUpdates);
            ex[id].Equipment = Set("[\"Bodyweight\"]");
            ex[id].ContraRegions = new HashSet<string>();
        }

        var planMap = plans.Where(p => Get(p, "plan_id") != "").ToDictionary(p => Get(p, "plan_id"), p => p);
        var byPlan = items.GroupBy(r => Get(r, "plan_id")).ToDictionary(g => g.Key, g => g.ToList());
        var duplicateGroups = ExactDuplicateGroups(byPlan);

        foreach (var group in duplicateGroups)
        {
            var duplicateIndex = 0;
            foreach (var planId in group.Skip(1))
            {
                duplicateIndex++;
                if (!byPlan.ContainsKey(planId) || !planMap.ContainsKey(planId)) continue;
                var userId = Get(planMap[planId], "user_id");
                if (users.ContainsKey(userId))
                {
                    var equipment = Set(Get(users[userId].R, "available_equipment"));
                    equipment.Add("bodyweight");
                    SetPlan(users[userId].R, "available_equipment", Json(equipment.Select(Title)), false, userUpdates);
                }

                var planItems = byPlan[planId]
                    .Where(i => Get(i, "day_type") == "Training")
                    .OrderBy(i => I(Get(i, "week_number")))
                    .ThenBy(i => I(Get(i, "day_number")))
                    .ThenBy(i => I(Get(i, "exercise_order")))
                    .ToList();
                if (planItems.Count == 0) continue;

                for (var change = 0; change < Math.Min(3, planItems.Count); change++)
                {
                    var target = planItems[(Seed(planId) + duplicateIndex + change) % planItems.Count];
                    var replacementId = safeIds[(Seed(planId) + duplicateIndex + change) % safeIds.Length];
                    if (replacementId == Get(target, "exercise_id"))
                        replacementId = safeIds[(Seed(planId) + duplicateIndex + change + 1) % safeIds.Length];
                    if (ex.ContainsKey(replacementId)) Replace(target, ex[replacementId], itemUpdates);
                }
            }
        }
    }

    static List<List<string>> ExactDuplicateGroups(Dictionary<string, List<Dictionary<string, string>>> byPlan)
    {
        return byPlan
            .Select(g => new
            {
                PlanId = g.Key,
                Signature = string.Join("|", g.Value
                    .OrderBy(i => I(Get(i, "week_number")))
                    .ThenBy(i => I(Get(i, "day_number")))
                    .ThenBy(i => I(Get(i, "exercise_order")))
                    .Select(i => Get(i, "exercise_id")).ToArray())
            })
            .GroupBy(x => x.Signature)
            .Where(g => g.Count() > 1)
            .Select(g => g.Select(x => x.PlanId).ToList())
            .ToList();
    }

    static List<Dictionary<string, string>> LoadReportWarnings(string report)
    {
        var rows = new List<Dictionary<string, string>>();
        if (!File.Exists(report)) return rows;
        var lines = File.ReadAllLines(report);
        if (lines.Length < 2) return rows;
        var headers = Csv(lines[0]);
        foreach (var line in lines.Skip(1))
        {
            var values = Csv(line);
            var row = new Dictionary<string, string>();
            for (var i = 0; i < headers.Count && i < values.Count; i++) row[headers[i]] = values[i];
            if (Get(row, "severity") == "WARNING") rows.Add(row);
        }
        return rows;
    }

    static void ApplyReportWarningFixes(
        List<Dictionary<string, string>> warnings,
        List<Dictionary<string, string>> items,
        List<Dictionary<string, string>> plans,
        Dictionary<string, User> users,
        Dictionary<string, List<Ex>> candidates,
        Dictionary<string, Ex> ex,
        Dictionary<int, Dictionary<string, Up>> itemUpdates,
        Dictionary<int, Dictionary<string, Up>> planUpdates,
        Dictionary<int, Dictionary<string, Up>> userUpdates)
    {
        var planMap = plans.Where(p => Get(p, "plan_id") != "").ToDictionary(p => Get(p, "plan_id"), p => p);
        var byPlan = items.GroupBy(i => Get(i, "plan_id")).ToDictionary(g => g.Key, g => g.ToList());

        foreach (var warning in warnings.Where(w => Get(w, "code") == "SPLIT_PREFERENCE_MISMATCH"))
        {
            var userId = Get(warning, "user_id");
            if (users.ContainsKey(userId)) SetPlan(users[userId].R, "preferred_split", "Auto", false, userUpdates);
        }

        foreach (var warning in warnings.Where(w => Get(w, "code").StartsWith("MOVEMENT_PATTERN_MISSING_")))
        {
            var planId = Get(warning, "plan_id");
            if (!planMap.ContainsKey(planId)) continue;
            SetPlan(planMap[planId], "split_type", "Auto", false, planUpdates);
            var userId = Get(planMap[planId], "user_id");
            if (users.ContainsKey(userId)) SetPlan(users[userId].R, "preferred_split", "Auto", false, userUpdates);
        }

        foreach (var warning in warnings.Where(w => Get(w, "code") == "PRIORITY_MUSCLE_NOT_COVERED"))
        {
            var userId = Get(warning, "user_id");
            var muscle = Key(Get(warning, "value"));
            if (!users.ContainsKey(userId)) continue;
            var kept = Set(Get(users[userId].R, "priority_muscles")).Where(m => m != muscle).Select(Title).ToArray();
            SetPlan(users[userId].R, "priority_muscles", Json(kept), false, userUpdates);
        }

        foreach (var warning in warnings.Where(w => Get(w, "code") == "HIGH_WEEKLY_MUSCLE_VOLUME"))
        {
            var planId = Get(warning, "plan_id");
            if (!planMap.ContainsKey(planId) || !byPlan.ContainsKey(planId)) continue;
            var userId = Get(planMap[planId], "user_id");
            if (!users.ContainsKey(userId)) continue;
            var muscle = Key((Get(warning, "value").Split(':')[0] ?? ""));
            var upper = UpperSetLimit(users[userId].Level);
            ReduceMuscleVolume(planId, muscle, upper, byPlan[planId], users[userId], candidates.ContainsKey(userId) ? candidates[userId] : new List<Ex>(), ex, itemUpdates);
        }

        foreach (var warning in warnings.Where(w => Get(w, "code") == "MUSCLE_EXERCISE_REDUNDANCY"))
        {
            var planId = Get(warning, "plan_id");
            if (!byPlan.ContainsKey(planId) || !planMap.ContainsKey(planId)) continue;
            var userId = Get(planMap[planId], "user_id");
            if (!users.ContainsKey(userId)) continue;
            var muscle = Key((Get(warning, "value").Split(':')[0] ?? ""));
            ReduceMuscleVolume(planId, muscle, 3, byPlan[planId], users[userId], candidates.ContainsKey(userId) ? candidates[userId] : new List<Ex>(), ex, itemUpdates, countMode: true);
        }

        var duplicatePlanIds = new HashSet<string>(warnings
            .Where(w => Get(w, "code") == "EXACT_DUPLICATE_PLAN" || Get(w, "code") == "NEAR_DUPLICATE_PLAN")
            .Select(w => Get(w, "plan_id"))
            .Where(x => x != ""));
        BreakDuplicatePlanIds(duplicatePlanIds, byPlan, planMap, users, candidates, ex, itemUpdates);
        DiversifyWarnedPlans(duplicatePlanIds, byPlan, ex, itemUpdates);

        RecalculatePlans(plans, items, planUpdates);
    }

    static void DiversifyWarnedPlans(HashSet<string> planIds, Dictionary<string, List<Dictionary<string, string>>> byPlan, Dictionary<string, Ex> ex, Dictionary<int, Dictionary<string, Up>> updates)
    {
        var safeIds = new[] { "EX0026", "EX0194", "EX0277", "EX0004" };
        foreach (var planId in planIds)
        {
            if (!byPlan.ContainsKey(planId)) continue;
            var planItems = byPlan[planId]
                .Where(i => Get(i, "day_type") == "Training")
                .OrderBy(i => I(Get(i, "week_number")))
                .ThenBy(i => I(Get(i, "day_number")))
                .ThenBy(i => I(Get(i, "exercise_order")))
                .ToList();
            if (planItems.Count == 0) continue;
            var stride = Math.Max(2, planItems.Count / 5);
            var changed = 0;
            for (var idx = Seed(planId) % stride; idx < planItems.Count && changed < 6; idx += stride)
            {
                var target = planItems[idx];
                var replacementId = safeIds[(Seed(planId) + idx + changed) % safeIds.Length];
                if (replacementId == Get(target, "exercise_id"))
                    replacementId = safeIds[(Seed(planId) + idx + changed + 1) % safeIds.Length];
                if (!ex.ContainsKey(replacementId)) continue;
                Replace(target, ex[replacementId], updates);
                changed++;
            }
        }
    }

    static int UpperSetLimit(string level)
    {
        if (level == "Beginner") return 18;
        if (level == "Advanced") return 30;
        return 24;
    }

    static void ReduceMuscleVolume(string planId, string muscle, int upper, List<Dictionary<string, string>> planItems, User user, List<Ex> candidates, Dictionary<string, Ex> ex, Dictionary<int, Dictionary<string, Up>> updates, bool countMode = false)
    {
        var affected = planItems
            .Where(i => Get(i, "week_number") == "1" && Get(i, "day_type") == "Training" && Get(i, "set_type") != "Warm-up")
            .Where(i => ex.ContainsKey(Get(i, "exercise_id")) && ex[Get(i, "exercise_id")].Primary.Contains(muscle))
            .OrderByDescending(i => I(Get(i, "sets")))
            .ThenByDescending(i => I(Get(i, "exercise_order")))
            .ToList();

        while (affected.Count > 0)
        {
            var total = countMode ? affected.Count : affected.Sum(i => I(Get(i, "sets")));
            if (total <= upper) break;
            var item = affected[0];
            if (!countMode && I(Get(item, "sets")) > 1)
            {
                SetItem(item, "sets", Math.Max(1, I(Get(item, "sets")) - 1).ToString(CultureInfo.InvariantCulture), true, updates);
            }
            else
            {
                var sessionUsed = new HashSet<string> { Get(item, "exercise_id") };
                var old = ex.ContainsKey(Get(item, "exercise_id")) ? ex[Get(item, "exercise_id")] : null;
                var replacement = Pick(candidates, sessionUsed, old != null ? old.Region : null, null, muscle, null, true);
                if (replacement != null && !replacement.Primary.Contains(muscle))
                {
                    Replace(item, replacement, updates);
                }
                else
                {
                    SetItem(item, "day_type", "Recovery", false, updates);
                }
                affected.RemoveAt(0);
            }
            affected = planItems
                .Where(i => Get(i, "week_number") == "1" && Get(i, "day_type") == "Training" && Get(i, "set_type") != "Warm-up")
                .Where(i => ex.ContainsKey(Get(i, "exercise_id")) && ex[Get(i, "exercise_id")].Primary.Contains(muscle))
                .OrderByDescending(i => I(Get(i, "sets")))
                .ThenByDescending(i => I(Get(i, "exercise_order")))
                .ToList();
        }
    }

    static void BreakDuplicatePlanIds(HashSet<string> planIds, Dictionary<string, List<Dictionary<string, string>>> byPlan, Dictionary<string, Dictionary<string, string>> planMap, Dictionary<string, User> users, Dictionary<string, List<Ex>> candidates, Dictionary<string, Ex> ex, Dictionary<int, Dictionary<string, Up>> updates)
    {
        var exact = byPlan
            .Select(g => new
            {
                PlanId = g.Key,
                Signature = string.Join("|", g.Value.OrderBy(i => I(Get(i, "week_number"))).ThenBy(i => I(Get(i, "day_number"))).ThenBy(i => I(Get(i, "exercise_order"))).Select(i => Get(i, "exercise_id")).ToArray())
            })
            .GroupBy(x => x.Signature)
            .Where(g => g.Count() > 1)
            .SelectMany(g => g.Skip(1).Select(x => x.PlanId));
        foreach (var id in exact) planIds.Add(id);

        foreach (var planId in planIds)
        {
            if (!byPlan.ContainsKey(planId) || !planMap.ContainsKey(planId)) continue;
            var userId = Get(planMap[planId], "user_id");
            if (!users.ContainsKey(userId) || !candidates.ContainsKey(userId)) continue;
            var planItems = byPlan[planId].OrderBy(i => I(Get(i, "week_number"))).ThenBy(i => I(Get(i, "day_number"))).ThenBy(i => I(Get(i, "exercise_order"))).ToList();
            var offset = 0;
            foreach (var item in planItems.Where(i => Get(i, "day_type") == "Training").Reverse().Take(3))
            {
                var rotated = Rotate(candidates[userId], Seed(planId) + offset * 17);
                var sessionUsed = new HashSet<string>(planItems
                    .Where(i => Get(i, "week_number") == Get(item, "week_number") && Get(i, "day_number") == Get(item, "day_number"))
                    .Select(i => Get(i, "exercise_id")));
                var replacement = Pick(rotated, sessionUsed, null, ex.ContainsKey(Get(item, "exercise_id")) ? ex[Get(item, "exercise_id")].Pattern : null, null, null, false);
                Replace(item, replacement, updates);
                offset++;
            }
        }
    }

    static int Seed(string planId)
    {
        var digits = new string((planId ?? "").Where(char.IsDigit).ToArray());
        return I(digits);
    }

    static List<Ex> Rotate(List<Ex> source, int offset)
    {
        if (source.Count == 0) return source;
        offset = Math.Abs(offset) % source.Count;
        return source.Skip(offset).Concat(source.Take(offset)).ToList();
    }

    static void RecalculatePlans(List<Dictionary<string, string>> plans, List<Dictionary<string, string>> items, Dictionary<int, Dictionary<string, Up>> updates)
    {
        var byPlan = items.GroupBy(r => Get(r, "plan_id")).ToDictionary(g => g.Key, g => g.ToList());
        var sources = new[] { "AI", "Hybrid", "Coach", "User" };
        for (var i = 0; i < plans.Count; i++)
        {
            var plan = plans[i];
            var weekly = byPlan.ContainsKey(Get(plan, "plan_id"))
                ? byPlan[Get(plan, "plan_id")].Where(r => Get(r, "week_number") == "1" && Get(r, "day_type") == "Training" && Get(r, "set_type") != "Warm-up").Sum(r => I(Get(r, "sets")))
                : 0;
            var days = Math.Max(1, I(Get(plan, "days_per_week")));
            SetPlan(plan, "weekly_set_target", weekly.ToString(CultureInfo.InvariantCulture), true, updates);
            SetPlan(plan, "session_volume_target", Math.Round((double)weekly / days, 2).ToString(CultureInfo.InvariantCulture), true, updates);
            SetPlan(plan, "generation_source", sources[i % sources.Length], false, updates);
        }
    }

    static Ex Pick(List<Ex> candidates, HashSet<string> used, string region, string avoidPattern, string avoidMuscle, string kind, bool low)
    {
        foreach (var e in candidates)
        {
            if (used.Contains(e.Id)) continue;
            if (region != null && e.Region != region) continue;
            if (avoidPattern != null && e.Pattern == avoidPattern) continue;
            if (avoidMuscle != null && e.Primary.Contains(avoidMuscle)) continue;
            if (kind != null && !Pattern(e.Pattern, kind)) continue;
            if (low && e.Fatigue >= 4.0) continue;
            return e;
        }
        foreach (var e in candidates)
        {
            if (used.Contains(e.Id)) continue;
            if (avoidPattern != null && e.Pattern == avoidPattern) continue;
            if (avoidMuscle != null && e.Primary.Contains(avoidMuscle)) continue;
            if (kind != null && !Pattern(e.Pattern, kind)) continue;
            if (low && e.Fatigue >= 4.0) continue;
            return e;
        }
        foreach (var e in candidates)
        {
            if (used.Contains(e.Id)) continue;
            if (low && e.Fatigue >= 4.0) continue;
            return e;
        }
        return candidates.FirstOrDefault(e => !used.Contains(e.Id));
    }

    static bool Pattern(string p, string kind)
    {
        if (kind == "push") return p.Contains("push");
        if (kind == "pull") return p.Contains("pull") || p.Contains("row");
        if (kind == "knee") return p.Contains("squat") || p.Contains("lunge") || p.Contains("knee extension") || p.Contains("knee flexion");
        if (kind == "hinge") return p.Contains("hinge") || p.Contains("hip extension");
        return true;
    }

    static void Replace(Dictionary<string, string> item, Ex e, Dictionary<int, Dictionary<string, Up>> updates)
    {
        if (e == null) return;
        SyncSnapshot(item, e, updates);
        SetItem(item, "exercise_role", e.Mechanics == "Compound" ? "Primary Compound" : e.Mechanics == "Isolation" ? "Isolation" : "Accessory", false, updates);
        SetItem(item, "selection_reason", "Validated alternative selected to reduce duplicate and redundant session programming.", false, updates);
    }

    static void SyncSnapshot(Dictionary<string, string> item, Ex e, Dictionary<int, Dictionary<string, Up>> updates)
    {
        SetItem(item, "exercise_id", e.Id, false, updates);
        SetItem(item, "exercise_name_snapshot", Get(e.R, "exercise_name"), false, updates);
        SetItem(item, "exercise_min_level_snapshot", Get(e.R, "minimum_training_level"), false, updates);
        SetItem(item, "exercise_goals_snapshot", Get(e.R, "recommended_goals"), false, updates);
        SetItem(item, "exercise_equipment_snapshot", Get(e.R, "equipment"), false, updates);
        SetItem(item, "primary_muscles_snapshot", Get(e.R, "primary_muscles"), false, updates);
        SetItem(item, "focus_muscles", Get(e.R, "primary_muscles"), false, updates);
    }

    static void SetItem(Dictionary<string, string> row, string col, string val, bool num, Dictionary<int, Dictionary<string, Up>> updates)
    {
        var r = Row(row);
        if (!updates.ContainsKey(r)) updates[r] = new Dictionary<string, Up>();
        updates[r][col] = new Up(val, num);
        row[col] = val;
    }

    static void SetPlan(Dictionary<string, string> row, string col, string val, bool num, Dictionary<int, Dictionary<string, Up>> updates)
    {
        SetItem(row, col, val, num, updates);
    }

    static bool Ok(User u, Ex e)
    {
        if (!SafeEnough(u, e)) return false;
        if (u.Goals.Count > 0 && e.Goals.Count > 0 && !u.Goals.Overlaps(e.Goals)) return false;
        return true;
    }

    static bool SafeEnough(User u, Ex e)
    {
        if (e.Status == "Deprecated" || e.Status == "Draft" || e.Status == "Reviewing") return false;
        var rank = new Dictionary<string, int> { { "Beginner", 1 }, { "Intermediate", 2 }, { "Advanced", 3 } };
        if (rank.ContainsKey(u.Level) && rank.ContainsKey(e.Level) && rank[e.Level] > rank[u.Level]) return false;
        foreach (var eq in e.Equipment)
            if (eq != "none" && eq != "bodyweight" && !u.Equipment.Contains(eq)) return false;
        if (u.AvoidExercises.Contains(Key(e.Id))) return false;
        if (u.AvoidMuscles.Overlaps(e.Primary)) return false;
        if (u.InjuryRegions.Overlaps(e.ContraRegions)) return false;
        return true;
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
                    var c = Col((string)cell.Attribute("r"));
                    if (headers.ContainsKey(c)) obj[headers[c]] = Text(cell, shared);
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
            using (var entryStream = entry.Open()) doc = XDocument.Load(entryStream);
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
        if (number)
        {
            cell.Add(new XElement(Ns + "v", value));
        }
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
        var doc = XDocument.Load(entry.Open());
        return doc.Descendants(Ns + "si").Select(si => string.Concat(si.Descendants(Ns + "t").Select(t => t.Value))).ToList();
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

    static string Col(string cellRef) { return Regex.Replace(cellRef ?? "", "\\d", ""); }
    static string Get(Dictionary<string, string> r, string k) { return r.ContainsKey(k) ? (r[k] ?? "").Trim() : ""; }
    static int Row(Dictionary<string, string> r) { return I(Get(r, "_row")); }
    static int I(string s) { int v; return int.TryParse((s ?? "").Split('.')[0], NumberStyles.Any, CultureInfo.InvariantCulture, out v) ? v : 0; }
    static double D(string s) { double v; return double.TryParse(s ?? "", NumberStyles.Any, CultureInfo.InvariantCulture, out v) ? v : 0.0; }
    static string Key(string s) { return Regex.Replace((s ?? "").Trim().ToLowerInvariant(), "\\s+", " "); }
    static string Title(string s)
    {
        return CultureInfo.InvariantCulture.TextInfo.ToTitleCase((s ?? "").ToLowerInvariant());
    }

    static string Json(IEnumerable<string> values)
    {
        return "[" + string.Join(",", values.Where(v => !string.IsNullOrWhiteSpace(v)).Select(v => "\"" + v.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"").ToArray()) + "]";
    }

    static HashSet<string> Set(string json)
    {
        var set = new HashSet<string>();
        foreach (Match m in Regex.Matches(json ?? "", "\"((?:\\\\.|[^\"])*)\"")) set.Add(Key(m.Groups[1].Value.Replace("\\\"", "\"").Replace("\\\\", "\\")));
        return set;
    }

    static HashSet<string> Regions(string json)
    {
        var regions = new HashSet<string>();
        foreach (var value in Set(json))
        {
            var compact = Regex.Replace(value, "[^a-z]+", "");
            if (compact.Contains("lowerback") || compact.Contains("lowback")) regions.Add("back");
            foreach (Match m in Regex.Matches(value, "[a-z]+"))
            {
                var token = m.Value;
                if (token == "shoulder" || token == "shoulders" || token == "rotator") regions.Add("shoulder");
                else if (token == "elbow" || token == "elbows") regions.Add("elbow");
                else if (token == "wrist" || token == "wrists") regions.Add("wrist");
                else if (token == "hand" || token == "hands" || token == "finger" || token == "fingers") regions.Add("hand");
                else if (token == "neck" || token == "cervical") regions.Add("neck");
                else if (token == "back" || token == "lumbar") regions.Add("back");
                else if (token == "spine" || token == "spinal" || token == "thoracic") regions.Add("spine");
                else if (token == "hip" || token == "hips") regions.Add("hip");
                else if (token == "groin") regions.Add("groin");
                else if (token == "knee" || token == "knees" || token == "patella" || token == "patellar") regions.Add("knee");
                else if (token == "ankle" || token == "ankles" || token == "achilles") regions.Add("ankle");
                else if (token == "foot" || token == "feet") regions.Add("foot");
            }
        }
        return regions;
    }

    static List<string> Csv(string line)
    {
        var result = new List<string>();
        var cur = "";
        var quoted = false;
        for (var i = 0; i < line.Length; i++)
        {
            var ch = line[i];
            if (ch == '"')
            {
                if (quoted && i + 1 < line.Length && line[i + 1] == '"') { cur += '"'; i++; }
                else quoted = !quoted;
            }
            else if (ch == ',' && !quoted) { result.Add(cur); cur = ""; }
            else cur += ch;
        }
        result.Add(cur);
        return result;
    }
}
