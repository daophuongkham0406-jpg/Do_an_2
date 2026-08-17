import 'package:flutter/material.dart';

import '../../core/api_service.dart';
import '../../core/app_colors.dart';
import '../../shared/exercise_images.dart';
import '../../shared/ui.dart';

class PlanScreen extends StatefulWidget {
  const PlanScreen({required this.user, super.key});

  final AppUser user;

  @override
  State<PlanScreen> createState() => _PlanScreenState();
}

class _PlanScreenState extends State<PlanScreen> {
  final _api = const ApiService();
  final _height = TextEditingController();
  final _weight = TextEditingController();
  final _age = TextEditingController();
  final _note = TextEditingController();
  final _priorityMuscles = TextEditingController();
  final _avoidNotes = TextEditingController();
  final _manualCalories = TextEditingController();
  final _manualProtein = TextEditingController();
  final _foodText = TextEditingController();

  String _goal = 'Tăng cơ';
  String _level = 'Trung bình';
  String _gender = 'Prefer not to say';
  String _intensity = 'Vừa phải';
  int _trainingDays = 3;
  int _sessionMinutes = 60;
  int _duration = 7;
  int _dayIndex = 0;
  int _nutritionTab = 0;
  bool _premium = false;
  bool _loading = false;
  bool _generating = false;
  bool _saving = false;
  bool _nutritionLoading = false;

  Map<String, dynamic>? _activePlan;
  Map<String, dynamic>? _draftPlan;
  Map<String, dynamic> _nutrition = {};
  String? _activePlanId;
  Set<int> _weekdays = {1, 3, 5};
  final Map<int, Set<int>> _weeklyWeekdays = {};

  @override
  void initState() {
    super.initState();
    _loadInitial();
  }

  @override
  void dispose() {
    _height.dispose();
    _weight.dispose();
    _age.dispose();
    _note.dispose();
    _priorityMuscles.dispose();
    _avoidNotes.dispose();
    _manualCalories.dispose();
    _manualProtein.dispose();
    _foodText.dispose();
    super.dispose();
  }

  String get _today => DateTime.now().toIso8601String().split('T').first;

  List<Map<String, dynamic>> get _days {
    final raw = (_draftPlan ?? _activePlan)?['days'];
    if (raw is! List) return const [];
    return raw
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }

  Map<String, dynamic> get _currentDay {
    final days = _days;
    if (days.isEmpty) return {};
    return days[_dayIndex.clamp(0, days.length - 1)];
  }

  bool get _hasActivePlan => _activePlan != null && _activePlanId != null;
  bool get _hasDraft => _draftPlan != null;

  double? get _bmi {
    final h = double.tryParse(_height.text.trim());
    final w = double.tryParse(_weight.text.trim());
    if (h == null || w == null || h < 100 || w < 20) return null;
    return w / ((h / 100) * (h / 100));
  }

  String _bmiCategory(double bmi) {
    if (bmi < 18.5) return 'Thiếu cân';
    if (bmi < 25) return 'Bình thường';
    if (bmi < 30) return 'Thừa cân';
    return 'Béo phì';
  }

  Future<void> _loadInitial() async {
    setState(() => _loading = true);
    final results = await Future.wait([
      _api.get('/api/payment/status/${widget.user.id}'),
      _api.get('/api/plans/get-active-plan?userId=${widget.user.id}'),
    ]);
    if (!mounted) return;
    final pay = _api.mapFrom(results[0].body);
    final activeBody = _api.mapFrom(results[1].body);
    final activePlan = _api.mapFrom(activeBody['plan']);

    setState(() {
      _premium = pay['isPremium'] == true ||
          widget.user.isPremium ||
          widget.user.isAdmin;
      if (results[1].ok && activePlan.isNotEmpty) {
        _activePlan = _normalizeSavedPlan(activePlan);
        _activePlanId = (activePlan['id'] ?? activePlan['_id'])?.toString();
        _draftPlan = null;
        _dayIndex = _nextOpenDayIndex(_activePlan!);
      } else {
        _activePlan = null;
        _activePlanId = null;
        _dayIndex = 0;
      }
      _loading = false;
    });
    await _loadNutrition();
  }

  Map<String, dynamic> _normalizeSavedPlan(Map<String, dynamic> saved) {
    final planData = saved['plan_data'] is Map
        ? Map<String, dynamic>.from(saved['plan_data'] as Map)
        : <String, dynamic>{};
    final progress = saved['daily_progress'] is List
        ? saved['daily_progress'] as List
        : const [];
    final progressByDay = <int, Map<String, dynamic>>{};
    for (final item in progress) {
      if (item is! Map) continue;
      final day = Map<String, dynamic>.from(item);
      final number = _safeInt(day['day_number'], 0);
      if (number > 0) progressByDay[number] = day;
    }

    final days =
        (planData['days'] is List ? planData['days'] as List : const [])
            .whereType<Map>()
            .map((rawDay) {
      final source = Map<String, dynamic>.from(rawDay);
      final number = _safeInt(source['day_number'], 0);
      final progressDay = progressByDay[number] ?? {};
      final progressExercises = progressDay['exercises'] is List
          ? progressDay['exercises'] as List
          : null;
      return {
        ...source,
        if (progressDay.isNotEmpty) ...progressDay,
        'day_number': number == 0 ? source['day_number'] : number,
        'exercises': progressExercises ?? source['exercises'] ?? const [],
        'completed': progressDay['day_done'] == true,
      };
    }).toList();

    return {
      ...planData,
      'id': saved['id'] ?? saved['_id'],
      'status': saved['status'],
      'created_at': saved['created_at'],
      'plan_name': planData['plan_name'] ??
          planData['title'] ??
          'Lộ trình đang thực hiện',
      'days': days,
      'duration_days': planData['duration_days'] ?? days.length,
    };
  }

  int _nextOpenDayIndex(Map<String, dynamic> plan) {
    final raw = plan['days'];
    if (raw is! List) return 0;
    final index =
        raw.indexWhere((item) => item is Map && item['completed'] != true);
    return index < 0 ? 0 : index;
  }

  Future<void> _loadNutrition() async {
    final result = await _api
        .get('/api/get-nutrition?userId=${widget.user.id}&date=$_today');
    if (!mounted) return;
    if (result.ok) setState(() => _nutrition = _api.mapFrom(result.body));
  }

  Future<void> _generatePlan() async {
    final h = double.tryParse(_height.text.trim());
    final w = double.tryParse(_weight.text.trim());
    final a = int.tryParse(_age.text.trim());
    if (h == null || w == null || a == null) {
      showAppSnack(context, 'Vui lòng nhập chiều cao, cân nặng và tuổi.',
          error: true);
      return;
    }
    final weeklyWeekdays = _weeklyWeekdayNumbers();
    final selectedWeekdays = _duration > 7
        ? _orderedWeekdays(weeklyWeekdays.expand((days) => days).toSet())
        : _orderedWeekdays(_weekdays);
    if (_duration > 7 && weeklyWeekdays.any((days) => days.isEmpty)) {
      showAppSnack(context, 'Vui lòng chọn ít nhất 1 ngày rảnh cho mỗi tuần.',
          error: true);
      return;
    }
    if (selectedWeekdays.isEmpty) {
      showAppSnack(context, 'Vui lòng chọn ít nhất 1 ngày rảnh.', error: true);
      return;
    }
    final trainingDaysCount = weeklyWeekdays.isEmpty
        ? selectedWeekdays.length
        : weeklyWeekdays.fold<int>(
            1, (max, days) => days.length > max ? days.length : max);
    var goalForRequest = _goal;
    final bmi = w / ((h / 100) * (h / 100));
    final suggestedGoal = _suggestGoalForBmi(bmi, goalForRequest);
    if (suggestedGoal != null) {
      final choice = await _confirmBmiGoal(
        bmi: bmi,
        currentGoal: goalForRequest,
        suggestedGoal: suggestedGoal,
      );
      if (!mounted || choice == null) return;
      goalForRequest = choice;
      if (choice != _goal) setState(() => _goal = choice);
    }

    setState(() {
      _generating = true;
      _draftPlan = null;
      _dayIndex = 0;
    });
    final avoidText = [_note.text.trim(), _avoidNotes.text.trim()]
        .where((text) => text.isNotEmpty)
        .join('. ');
    final result = await _api.post('/api/ml/generate-plan', {
      'goal': goalForRequest,
      'level': _level,
      'height': h,
      'weight': w,
      'age': a,
      'gender': _gender,
      'duration_days': _duration,
      'training_days_per_week': trainingDaysCount,
      'available_training_day_numbers': selectedWeekdays,
      'weekly_available_training_day_numbers': weeklyWeekdays,
      'session_duration_minutes': _sessionMinutes,
      'intensity_preference': _intensity,
      'priority_muscles': _priorityMuscles.text.trim(),
      'avoid_notes': avoidText,
      'note': avoidText,
      'userInfo': _note.text.trim(),
      'userId': widget.user.id,
    });
    if (!mounted) return;
    setState(() => _generating = false);

    if (!result.ok) {
      showAppSnack(context, result.message ?? 'Không tạo được lộ trình AI.',
          error: true);
      return;
    }
    final body = _api.mapFrom(result.body);
    final plan = _api.mapFrom(body['plan_data']);
    if (plan.isEmpty) {
      showAppSnack(context, 'Backend không trả về plan_data.', error: true);
      return;
    }
    setState(() {
      _draftPlan = plan;
      _dayIndex = 0;
    });
    showAppSnack(context, 'Đã tạo bản nháp. Kiểm tra rồi bấm áp dụng.');
  }

  Future<void> _saveDraft() async {
    final plan = _draftPlan;
    if (plan == null) return;
    setState(() => _saving = true);
    final result = await _api.post('/api/plans/save-ai-plan', {
      'plan_data': plan,
      'userId': widget.user.id,
      'source': 'ai_exercises_csv_rule_engine',
      'input_snapshot': {
        'height': _height.text.trim(),
        'weight': _weight.text.trim(),
        'age': _age.text.trim(),
        'goal': _goal,
        'level': _level,
        'gender': _gender,
        'duration_days': _duration,
        'training_days_per_week': _trainingDays,
        'available_training_day_numbers': _orderedWeekdays(_weekdays),
        'weekly_available_training_day_numbers': _weeklyWeekdayNumbers(),
        'session_duration_minutes': _sessionMinutes,
        'intensity_preference': _intensity,
        'priority_muscles': _priorityMuscles.text.trim(),
        'avoid_notes': _avoidNotes.text.trim(),
        'note': _note.text.trim(),
      },
    });
    if (!mounted) return;
    setState(() => _saving = false);
    if (!result.ok || _api.mapFrom(result.body)['success'] == false) {
      showAppSnack(context, result.message ?? 'Không lưu được lộ trình.',
          error: true);
      return;
    }
    showAppSnack(context, 'Đã áp dụng lộ trình.');
    await _loadInitial();
  }

  Future<void> _cancelActivePlan() async {
    final confirm = await _confirm(
      title: 'Hủy lộ trình?',
      message:
          'Lộ trình đang tập và tiến độ hiện tại sẽ bị hủy. Hành động này không thể hoàn tác.',
      danger: true,
    );
    if (confirm != true) return;
    setState(() => _loading = true);
    final result =
        await _api.delete('/api/plans/cancel-active/${widget.user.id}');
    if (!mounted) return;
    showAppSnack(context, result.message ?? 'Đã hủy lộ trình.',
        error: !result.ok);
    await _loadInitial();
  }

  Future<void> _checkinExercise(Map<String, dynamic> exercise) async {
    final planId = _activePlanId;
    if (planId == null) return;
    final day = _currentDay;
    if (day['is_locked'] == true) {
      showAppSnack(context, 'Ngày này đã chốt sổ.', error: true);
      return;
    }
    final name =
        (exercise['name'] ?? exercise['exercise_name'] ?? '').toString();
    if (name.isEmpty) return;
    final result = await _api.post('/api/plans/checkin-exercise', {
      'planId': planId,
      'plan_id': planId,
      'dayNumber': day['day_number'],
      'day_number': day['day_number'],
      'exerciseName': name,
      'exercise_name': name,
      'completed': true,
    });
    if (!mounted) return;
    showAppSnack(
      context,
      result.ok
          ? 'Đã cập nhật bài tập.'
          : result.message ?? 'Không cập nhật được.',
      error: !result.ok,
    );
    await _loadInitial();
  }

  Future<void> _checkinRestDay() async {
    final planId = _activePlanId;
    if (planId == null) return;
    final day = _currentDay;
    final result = await _api.post('/api/plans/checkin-exercise', {
      'planId': planId,
      'plan_id': planId,
      'dayNumber': day['day_number'],
      'day_number': day['day_number'],
      'exerciseName': 'RestDay',
      'exercise_name': 'RestDay',
      'completed': true,
    });
    if (!mounted) return;
    showAppSnack(
      context,
      result.ok
          ? 'Đã hoàn thành ngày nghỉ.'
          : result.message ?? 'Không cập nhật được.',
      error: !result.ok,
    );
    await _loadInitial();
  }

  Future<void> _lockCurrentDay() async {
    final planId = _activePlanId;
    if (planId == null) return;
    final day = _currentDay;
    final confirm = await _confirm(
      title: 'Chốt sổ ngày ${day['day_number']}?',
      message:
          'Sau khi chốt sổ, bạn không thể sửa lại bài tập của ngày này trong app.',
    );
    if (confirm != true) return;
    final result = await _api.post('/api/plans/lock-day', {
      'planId': planId,
      'plan_id': planId,
      'dayNumber': day['day_number'],
      'day_number': day['day_number'],
    });
    if (!mounted) return;
    showAppSnack(context, result.message ?? 'Đã chốt sổ ngày tập.',
        error: !result.ok);
    await _loadInitial();
  }

  Future<void> _addManualNutrition() async {
    final calories = double.tryParse(_manualCalories.text.trim()) ?? 0;
    final protein = double.tryParse(_manualProtein.text.trim()) ?? 0;
    if (calories <= 0 && protein <= 0) {
      showAppSnack(context, 'Nhập calories hoặc protein trước.', error: true);
      return;
    }
    await _saveNutrition(calories, protein, 0, 0, 'Nhập tay');
    _manualCalories.clear();
    _manualProtein.clear();
  }

  Future<void> _analyzeFood() async {
    final text = _foodText.text.trim();
    if (text.isEmpty) {
      showAppSnack(context, 'Nhập món ăn cần phân tích.', error: true);
      return;
    }
    setState(() => _nutritionLoading = true);
    final result = await _api.post('/api/analyze-food', {'food_text': text});
    if (!mounted) return;
    setState(() => _nutritionLoading = false);
    if (!result.ok) {
      showAppSnack(context, result.message ?? 'Không phân tích được món ăn.',
          error: true);
      return;
    }
    final data = _api.mapFrom(_api.mapFrom(result.body)['data']);
    final total = _api.mapFrom(data['total']);
    final ok = await _confirm(
      title: 'Thêm món ăn?',
      message:
          '${data['summary'] ?? text}\n\nƯớc tính: ${_safeNum(total['calories']).toStringAsFixed(0)} kcal, ${_safeNum(total['protein']).toStringAsFixed(1)}g protein.',
    );
    if (ok == true) {
      await _saveNutrition(
        _safeNum(total['calories']),
        _safeNum(total['protein']),
        _safeNum(total['carbs']),
        _safeNum(total['fat']),
        text,
      );
      _foodText.clear();
    }
  }

  Future<void> _saveNutrition(
    double calories,
    double protein,
    double carbs,
    double fat,
    String note,
  ) async {
    setState(() => _nutritionLoading = true);
    final result = await _api.post('/api/save-nutrition', {
      'userId': widget.user.id,
      'date': _today,
      'calories': calories,
      'protein': protein,
      'carbs': carbs,
      'fat': fat,
      'note': note,
    });
    if (!mounted) return;
    setState(() => _nutritionLoading = false);
    if (!result.ok) {
      showAppSnack(context, result.message ?? 'Không lưu được dinh dưỡng.',
          error: true);
      return;
    }
    showAppSnack(context, 'Đã cộng dinh dưỡng hôm nay.');
    await _loadNutrition();
  }

  Future<void> _lockNutrition() async {
    final confirm = await _confirm(
      title: 'Chốt dinh dưỡng hôm nay?',
      message: 'Sau khi chốt, bạn không thể cộng thêm món cho ngày hôm nay.',
    );
    if (confirm != true) return;
    final result = await _api.post('/api/lock-nutrition', {
      'userId': widget.user.id,
      'date': _today,
    });
    if (!mounted) return;
    showAppSnack(context, result.message ?? 'Đã chốt dinh dưỡng.',
        error: !result.ok);
    await _loadNutrition();
  }

  Future<bool?> _confirm({
    required String title,
    required String message,
    bool danger = false,
  }) {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.bgCard,
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Đóng'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor:
                  danger ? AppColors.danger : AppColors.accentPurple,
            ),
            onPressed: () => Navigator.pop(context, true),
            child: Text(danger ? 'Xác nhận hủy' : 'Xác nhận'),
          ),
        ],
      ),
    );
  }

  Future<String?> _confirmBmiGoal({
    required double bmi,
    required String currentGoal,
    required String suggestedGoal,
  }) {
    return showModalBottomSheet<String>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return Container(
          padding: const EdgeInsets.fromLTRB(20, 18, 20, 20),
          decoration: const BoxDecoration(
            color: AppColors.bgCard,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: SafeArea(
            top: false,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'Gợi ý mục tiêu theo BMI',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 10),
                _BmiStrip(bmi: bmi, category: _bmiCategory(bmi)),
                const SizedBox(height: 12),
                Text(
                  'Mục tiêu hiện tại là "$currentGoal". Với chỉ số này, app gợi ý đổi sang "$suggestedGoal" để lộ trình hợp lý hơn.',
                  style:
                      const TextStyle(color: AppColors.textMuted, height: 1.45),
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: () => Navigator.pop(context, suggestedGoal),
                  child: Text('Đổi sang $suggestedGoal'),
                ),
                const SizedBox(height: 8),
                OutlinedButton(
                  onPressed: () => Navigator.pop(context, currentGoal),
                  child: const Text('Giữ mục tiêu hiện tại'),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final plan = _draftPlan ?? _activePlan;
    return Stack(
      children: [
        const Positioned.fill(child: GridBackground()),
        SafeArea(
          child: RefreshIndicator(
            onRefresh: _loadInitial,
            child: ListView(
              padding: const EdgeInsets.only(bottom: 96),
              children: [
                ScreenHeader(
                  title: _hasActivePlan
                      ? 'Lộ trình đang chạy'
                      : _hasDraft
                          ? 'Bản nháp lộ trình'
                          : 'Lộ trình cá nhân',
                  subtitle: _hasActivePlan
                      ? 'Check-in bài tập, chốt ngày và theo dõi dinh dưỡng.'
                      : 'Khảo sát nhanh để FIT ME tạo lịch tập cá nhân hóa.',
                  trailing: _loading
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : null,
                ),
                if (!_hasActivePlan) _buildCreator(),
                if (plan == null)
                  const Padding(
                    padding: EdgeInsets.all(20),
                    child: AppCard(
                      child: Text(
                        'Chưa có dữ liệu lộ trình. Điền thông tin và tạo bản nháp trước.',
                        style: TextStyle(color: AppColors.textMuted),
                      ),
                    ),
                  )
                else ...[
                  _PlanSummaryCard(
                    plan: plan,
                    draft: _hasDraft,
                    days: _days,
                    saving: _saving,
                    onSave: _saveDraft,
                    onRetry: _generatePlan,
                    onCancel: _hasActivePlan ? _cancelActivePlan : null,
                  ),
                  _buildDayNavigator(),
                  _buildCurrentDayCard(),
                  if (_hasActivePlan) _buildNutritionCard(),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildCreator() {
    final bmi = _bmi;
    final canLong = _premium;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SectionHeading(
              title: 'Khởi tạo',
              subtitle: 'Thông tin càng rõ, lộ trình càng sát.',
            ),
            const SizedBox(height: 14),
            _SelectField(
              label: 'Mục tiêu',
              value: _goal,
              values: const [
                'Tăng cân',
                'Tăng cơ',
                'Giảm mỡ',
                'Sức bền',
                'Sức mạnh'
              ],
              onChanged: (value) => setState(() => _goal = value),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _SelectField(
                    label: 'Kinh nghiệm',
                    value: _level,
                    values: const ['Người mới', 'Trung bình', 'Kỳ cựu'],
                    onChanged: (value) => setState(() => _level = value),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _SelectField(
                    label: 'Giới tính',
                    value: _gender,
                    values: const [
                      'Prefer not to say',
                      'Male',
                      'Female',
                      'Other'
                    ],
                    labelOf: _genderLabel,
                    onChanged: (value) => setState(() => _gender = value),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: AppTextField(
                    controller: _height,
                    label: 'Chiều cao',
                    hint: '170',
                    keyboardType: TextInputType.number,
                    onChanged: (_) => setState(() {}),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: AppTextField(
                    controller: _weight,
                    label: 'Cân nặng',
                    hint: '65',
                    keyboardType: TextInputType.number,
                    onChanged: (_) => setState(() {}),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: AppTextField(
                    controller: _age,
                    label: 'Tuổi',
                    hint: '24',
                    keyboardType: TextInputType.number,
                  ),
                ),
              ],
            ),
            if (bmi != null) ...[
              const SizedBox(height: 10),
              _BmiStrip(bmi: bmi, category: _bmiCategory(bmi)),
            ],
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: _SelectField(
                    label: 'Buổi / tuần',
                    value: '$_trainingDays',
                    values: const ['2', '3', '4', '5', '6'],
                    labelOf: (value) => '$value buổi',
                    onChanged: (value) {
                      final count = int.parse(value);
                      setState(() {
                        _setTrainingDays(count);
                      });
                    },
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _SelectField(
                    label: 'Thời lượng',
                    value: '$_sessionMinutes',
                    values: const ['30', '45', '60', '75', '90'],
                    labelOf: (value) => '$value phút',
                    onChanged: (value) =>
                        setState(() => _sessionMinutes = int.parse(value)),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            _SelectField(
              label: 'Cường độ',
              value: _intensity,
              values: const [
                'Vừa phải',
                'Nhẹ, ưu tiên an toàn',
                'Thử thách hơn'
              ],
              onChanged: (value) => setState(() => _intensity = value),
            ),
            const SizedBox(height: 14),
            const _FieldLabel('Độ dài lộ trình'),
            const SizedBox(height: 8),
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisSpacing: 8,
              mainAxisSpacing: 8,
              childAspectRatio: 2.55,
              children: [
                _DurationButton(
                  days: 7,
                  selected: _duration == 7,
                  locked: false,
                  onTap: () => setState(() => _setDuration(7)),
                ),
                _DurationButton(
                  days: 14,
                  selected: _duration == 14,
                  locked: false,
                  onTap: () => setState(() => _setDuration(14)),
                ),
                _DurationButton(
                  days: 21,
                  selected: _duration == 21,
                  locked: !canLong,
                  onTap: () => setState(() => _setDuration(21)),
                ),
                _DurationButton(
                  days: 30,
                  selected: _duration == 30,
                  locked: !canLong,
                  onTap: () => setState(() => _setDuration(30)),
                ),
              ],
            ),
            if (!canLong) ...[
              const SizedBox(height: 8),
              const Text(
                'Premium mở khóa lộ trình 21 và 30 ngày.',
                style: TextStyle(color: AppColors.textMuted, fontSize: 12),
              ),
            ],
            const SizedBox(height: 14),
            _FieldLabel(
              _duration > 7
                  ? 'Lịch rảnh theo từng tuần'
                  : 'Ngày rảnh trong tuần',
            ),
            const SizedBox(height: 8),
            if (_duration > 7)
              _WeeklyWeekdayPicker(
                weeks: _weeklyWeekdaySets(),
                onChanged: (index, days) => setState(() {
                  _weeklyWeekdays[index] = days;
                  _trainingDays = _weeklyWeekdayNumbers().fold<int>(
                    1,
                    (max, week) => week.length > max ? week.length : max,
                  );
                }),
              )
            else
              _WeekdayPicker(
                selected: _weekdays,
                minimumSelection: 1,
                onChanged: (days) => setState(() {
                  _weekdays = days;
                  _trainingDays = days.length.clamp(1, 6);
                }),
              ),
            const SizedBox(height: 14),
            AppTextField(
              controller: _priorityMuscles,
              label: 'Nhóm cơ ưu tiên',
              hint: 'Ví dụ: ngực, lưng, mông...',
            ),
            const SizedBox(height: 12),
            AppTextField(
              controller: _avoidNotes,
              label: 'Vùng đau / bài cần tránh',
              hint: 'Ví dụ: đau vai, đau gối, tránh squat nặng...',
            ),
            const SizedBox(height: 12),
            AppTextField(
              controller: _note,
              label: 'Ghi chú thêm',
              hint: 'Ví dụ: chỉ rảnh 45 phút/ngày...',
              maxLines: 3,
            ),
            const SizedBox(height: 16),
            PrimaryButton(
              label: 'Tạo lộ trình bằng AI',
              loading: _generating,
              onPressed: _generatePlan,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDayNavigator() {
    final days = _days;
    if (days.isEmpty) return const SizedBox.shrink();
    final day = _currentDay;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
      child: AppCard(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            IconButton.filledTonal(
              tooltip: 'Ngày trước',
              onPressed:
                  _dayIndex == 0 ? null : () => setState(() => _dayIndex--),
              icon: const Icon(Icons.chevron_left),
            ),
            Expanded(
              child: Column(
                children: [
                  Text(
                    'Ngày ${day['day_number'] ?? _dayIndex + 1} / ${days.length}',
                    style: const TextStyle(fontWeight: FontWeight.w900),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    '${day['focus'] ?? 'Tập luyện'}',
                    textAlign: TextAlign.center,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        color: AppColors.textMuted, fontSize: 12),
                  ),
                ],
              ),
            ),
            IconButton.filledTonal(
              tooltip: 'Ngày tiếp theo',
              onPressed: _dayIndex >= days.length - 1
                  ? null
                  : () => setState(() => _dayIndex++),
              icon: const Icon(Icons.chevron_right),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCurrentDayCard() {
    final day = _currentDay;
    if (day.isEmpty) return const SizedBox.shrink();
    final exercises = _exerciseList(day);
    final isRest = day['is_rest'] == true || exercises.isEmpty;
    final completed = day['completed'] == true || day['day_done'] == true;
    final locked = day['is_locked'] == true;
    final completedExercises =
        exercises.where((item) => item['completed'] == true).length;
    final totalExercises = exercises.length;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                _DayBadge(
                  label: 'Ngày ${day['day_number'] ?? _dayIndex + 1}',
                  done: completed,
                  locked: locked,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    '${day['focus'] ?? (isRest ? 'Nghỉ phục hồi' : 'Tập luyện')}',
                    style: const TextStyle(fontWeight: FontWeight.w900),
                  ),
                ),
                if (!isRest)
                  Text(
                    '$completedExercises/$totalExercises',
                    style: const TextStyle(
                      color: AppColors.accentYellow,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 12),
            _DayNutritionStrip(day: day),
            const SizedBox(height: 12),
            if (isRest)
              _RestDayBox(
                completed: completed,
                draft: _hasDraft,
                locked: locked,
                onComplete: _checkinRestDay,
              )
            else
              ...exercises.map(
                (exercise) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _ExerciseRow(
                    exercise: exercise,
                    draft: _hasDraft,
                    locked: locked,
                    onComplete: () => _checkinExercise(exercise),
                    onDetail: () => _openExerciseDetail(exercise),
                  ),
                ),
              ),
            if (_hasActivePlan) ...[
              const SizedBox(height: 6),
              if (locked)
                const _LockedMessage(text: 'Ngày này đã được chốt sổ.')
              else
                OutlinedButton.icon(
                  onPressed: _lockCurrentDay,
                  icon: const Icon(Icons.lock_outline),
                  label: Text(
                      'Chốt sổ ngày ${day['day_number'] ?? _dayIndex + 1}'),
                ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildNutritionCard() {
    final day = _currentDay;
    final targetCal = _safeNum(
      day['target_calories'],
      fallback: _safeNum((_activePlan ?? {})['daily_calories_workout'],
          fallback: 2000),
    );
    final targetProtein = _safeNum(
      day['target_protein'],
      fallback:
          _safeNum((_activePlan ?? {})['daily_protein_workout'], fallback: 130),
    );
    final calories = _safeNum(_nutrition['calories']);
    final protein = _safeNum(_nutrition['protein']);
    final locked = _nutrition['is_locked'] == true;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SectionHeading(
              title: 'Dinh dưỡng hôm nay',
              subtitle: locked ? 'Đã chốt sổ' : _today,
              trailing: _nutritionLoading
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : null,
            ),
            const SizedBox(height: 12),
            _MacroProgress(
              label: 'Calories',
              value: calories,
              target: targetCal,
              unit: 'kcal',
              color: AppColors.accentYellow,
            ),
            const SizedBox(height: 10),
            _MacroProgress(
              label: 'Protein',
              value: protein,
              target: targetProtein,
              unit: 'g',
              color: AppColors.success,
            ),
            const SizedBox(height: 14),
            SegmentedButton<int>(
              segments: const [
                ButtonSegment(value: 0, label: Text('Nhập tay')),
                ButtonSegment(value: 1, label: Text('Món ăn')),
              ],
              selected: {_nutritionTab},
              onSelectionChanged: locked
                  ? null
                  : (value) => setState(() => _nutritionTab = value.first),
            ),
            const SizedBox(height: 14),
            if (locked)
              const _LockedMessage(
                text: 'Bạn đã chốt dinh dưỡng hôm nay. Hẹn gặp lại ngày mai.',
              )
            else if (_nutritionTab == 0)
              _buildManualNutrition()
            else
              _buildFoodNutrition(),
            if (!locked) ...[
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: _lockNutrition,
                icon: const Icon(Icons.lock_outline),
                label: const Text('Chốt dinh dưỡng hôm nay'),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildManualNutrition() {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: AppTextField(
                controller: _manualCalories,
                label: 'Calories',
                hint: '500',
                keyboardType: TextInputType.number,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: AppTextField(
                controller: _manualProtein,
                label: 'Protein',
                hint: '30',
                keyboardType: TextInputType.number,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        PrimaryButton(
          label: 'Cộng vào hôm nay',
          loading: _nutritionLoading,
          onPressed: _addManualNutrition,
        ),
      ],
    );
  }

  Widget _buildFoodNutrition() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppTextField(
          controller: _foodText,
          label: 'Mô tả món ăn',
          hint: 'Ví dụ: 200g ức gà và 1 bát cơm',
          maxLines: 3,
        ),
        const SizedBox(height: 12),
        PrimaryButton(
          label: 'Phân tích và thêm',
          loading: _nutritionLoading,
          onPressed: _analyzeFood,
        ),
      ],
    );
  }

  void _openExerciseDetail(Map<String, dynamic> exercise) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _ExerciseDetailSheet(exercise: exercise),
    );
  }

  List<Map<String, dynamic>> _exerciseList(Map<String, dynamic> day) {
    final raw = day['exercises'];
    if (raw is! List) return const [];
    return raw
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }

  Set<int> _defaultWeekdays(int count) {
    const schedules = {
      1: {1},
      2: {1, 4},
      3: {1, 3, 5},
      4: {1, 2, 4, 6},
      5: {1, 2, 3, 5, 6},
      6: {1, 2, 3, 4, 5, 6},
    };
    return {...(schedules[count] ?? schedules[3]!)};
  }

  int get _weekCount {
    final count = (_duration / 7).ceil();
    if (count < 1) return 1;
    if (count > 4) return 4;
    return count;
  }

  List<int> _orderedWeekdays(Iterable<int> days) {
    final values = days.where((day) => day >= 1 && day <= 7).toSet().toList()
      ..sort();
    return values;
  }

  List<Set<int>> _weeklyWeekdaySets() {
    return List.generate(_weekCount, (index) {
      final days = _weeklyWeekdays[index];
      if (days != null && days.isNotEmpty) return {...days};
      return _weekdays.isEmpty
          ? _defaultWeekdays(_trainingDays)
          : {..._weekdays};
    });
  }

  List<List<int>> _weeklyWeekdayNumbers() {
    if (_duration <= 7) return const [];
    return _weeklyWeekdaySets().map((days) => _orderedWeekdays(days)).toList();
  }

  void _setTrainingDays(int count) {
    _trainingDays = count;
    _weekdays = _defaultWeekdays(count);
    _weeklyWeekdays
      ..clear()
      ..addEntries(List.generate(
        _weekCount,
        (index) => MapEntry(index, {..._weekdays}),
      ));
  }

  void _setDuration(int days) {
    _duration = days;
    if (days <= 7) return;
    final weekCount = _weekCount;
    _weeklyWeekdays.removeWhere((index, _) => index >= weekCount);
    for (var index = 0; index < weekCount; index++) {
      _weeklyWeekdays.putIfAbsent(index, () => {..._weekdays});
    }
  }

  String _genderLabel(String value) {
    return switch (value) {
      'Male' => 'Nam',
      'Female' => 'Nữ',
      'Other' => 'Khác',
      _ => 'Không nêu',
    };
  }

  String? _suggestGoalForBmi(double bmi, String goal) {
    if (bmi < 18.5 && (goal == 'Giảm mỡ' || goal == 'Sức bền')) {
      return 'Tăng cân';
    }
    if (bmi >= 27 && (goal == 'Tăng cân' || goal == 'Tăng cơ')) {
      return 'Giảm mỡ';
    }
    return null;
  }

  int _safeInt(dynamic value, int fallback) {
    if (value is int) return value;
    return int.tryParse('$value') ?? fallback;
  }

  double _safeNum(dynamic value, {double fallback = 0}) {
    if (value is num) return value.toDouble();
    return double.tryParse('$value') ?? fallback;
  }
}

class _PlanSummaryCard extends StatelessWidget {
  const _PlanSummaryCard({
    required this.plan,
    required this.draft,
    required this.days,
    required this.saving,
    required this.onSave,
    required this.onRetry,
    required this.onCancel,
  });

  final Map<String, dynamic> plan;
  final bool draft;
  final List<Map<String, dynamic>> days;
  final bool saving;
  final VoidCallback onSave;
  final VoidCallback onRetry;
  final VoidCallback? onCancel;

  @override
  Widget build(BuildContext context) {
    final done = days.where((day) => day['completed'] == true).length;
    final pct = days.isEmpty ? 0.0 : done / days.length;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${plan['plan_name'] ?? plan['title'] ?? 'Lộ trình FIT ME'}',
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 5),
                      Text(
                        draft
                            ? 'Bản nháp chưa áp dụng'
                            : '${plan['duration_days'] ?? days.length} ngày · $done/${days.length} ngày xong',
                        style: const TextStyle(color: AppColors.textMuted),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
                  decoration: BoxDecoration(
                    color: (draft ? AppColors.accentYellow : AppColors.success)
                        .withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    draft ? 'NHÁP' : 'ACTIVE',
                    style: TextStyle(
                      color: draft ? AppColors.accentYellow : AppColors.success,
                      fontWeight: FontWeight.w900,
                      fontSize: 11,
                    ),
                  ),
                ),
              ],
            ),
            if (!draft) ...[
              const SizedBox(height: 14),
              LinearProgressIndicator(
                value: pct,
                color: AppColors.accentYellow,
                backgroundColor: AppColors.bgInput,
              ),
              const SizedBox(height: 8),
              Text(
                '${(pct * 100).round()}% lộ trình',
                style:
                    const TextStyle(color: AppColors.textMuted, fontSize: 12),
              ),
            ],
            if (draft) ...[
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: PrimaryButton(
                      label: 'Áp dụng',
                      loading: saving,
                      onPressed: onSave,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: onRetry,
                      icon: const Icon(Icons.refresh),
                      label: const Text('Tạo lại'),
                    ),
                  ),
                ],
              ),
            ],
            if (onCancel != null) ...[
              const SizedBox(height: 12),
              OutlinedButton.icon(
                style:
                    OutlinedButton.styleFrom(foregroundColor: AppColors.danger),
                onPressed: onCancel,
                icon: const Icon(Icons.delete_outline),
                label: const Text('Hủy lộ trình đang tập'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _SelectField extends StatelessWidget {
  const _SelectField({
    required this.label,
    required this.value,
    required this.values,
    required this.onChanged,
    this.labelOf,
  });

  final String label;
  final String value;
  final List<String> values;
  final ValueChanged<String> onChanged;
  final String Function(String value)? labelOf;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _FieldLabel(label),
        const SizedBox(height: 7),
        DropdownButtonFormField<String>(
          initialValue: value,
          isExpanded: true,
          dropdownColor: AppColors.bgCard,
          decoration: InputDecoration(
            filled: true,
            fillColor: AppColors.bgInput,
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
          ),
          items: values
              .map(
                (item) => DropdownMenuItem(
                  value: item,
                  child: Text(labelOf?.call(item) ?? item),
                ),
              )
              .toList(),
          onChanged: (value) {
            if (value != null) onChanged(value);
          },
        ),
      ],
    );
  }
}

class _FieldLabel extends StatelessWidget {
  const _FieldLabel(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        color: AppColors.textMuted,
        fontSize: 12,
        fontWeight: FontWeight.w900,
      ),
    );
  }
}

class _WeekdayPicker extends StatelessWidget {
  const _WeekdayPicker({
    required this.selected,
    required this.onChanged,
    this.minimumSelection = 0,
  });

  final Set<int> selected;
  final ValueChanged<Set<int>> onChanged;
  final int minimumSelection;

  @override
  Widget build(BuildContext context) {
    const labels = {
      1: 'T2',
      2: 'T3',
      3: 'T4',
      4: 'T5',
      5: 'T6',
      6: 'T7',
      7: 'CN'
    };
    return Wrap(
      spacing: 7,
      runSpacing: 7,
      children: labels.entries.map((entry) {
        final active = selected.contains(entry.key);
        return ChoiceChip(
          label: Text(entry.value),
          selected: active,
          selectedColor: AppColors.accentYellow.withValues(alpha: 0.16),
          onSelected: (_) {
            final next = {...selected};
            if (active) {
              if (next.length <= minimumSelection) {
                showAppSnack(
                  context,
                  minimumSelection <= 1
                      ? 'Cần chọn ít nhất 1 ngày rảnh.'
                      : 'Cần chọn ít nhất $minimumSelection ngày rảnh.',
                  error: true,
                );
                return;
              }
              next.remove(entry.key);
            } else {
              next.add(entry.key);
            }
            onChanged(next);
          },
        );
      }).toList(),
    );
  }
}

class _WeeklyWeekdayPicker extends StatelessWidget {
  const _WeeklyWeekdayPicker({
    required this.weeks,
    required this.onChanged,
  });

  final List<Set<int>> weeks;
  final void Function(int index, Set<int> days) onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: List.generate(weeks.length, (index) {
        final days = weeks[index];
        return Container(
          margin: EdgeInsets.only(bottom: index == weeks.length - 1 ? 0 : 10),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppColors.bgInput,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppColors.border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    'Tuần ${index + 1}',
                    style: const TextStyle(fontWeight: FontWeight.w900),
                  ),
                  const Spacer(),
                  Text(
                    '${days.length} buổi',
                    style: const TextStyle(
                      color: AppColors.textMuted,
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              _WeekdayPicker(
                selected: days,
                minimumSelection: 1,
                onChanged: (next) => onChanged(index, next),
              ),
            ],
          ),
        );
      }),
    );
  }
}

class _DurationButton extends StatelessWidget {
  const _DurationButton({
    required this.days,
    required this.selected,
    required this.locked,
    required this.onTap,
  });

  final int days;
  final bool selected;
  final bool locked;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: locked ? null : onTap,
      borderRadius: BorderRadius.circular(8),
      child: Opacity(
        opacity: locked ? 0.42 : 1,
        child: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: selected
                ? AppColors.accentYellow.withValues(alpha: 0.1)
                : AppColors.bgInput,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: selected ? AppColors.accentYellow : AppColors.border,
            ),
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  '$days ngày\n${days == 7 ? 'Tuần đầu' : days == 14 ? '2 tuần' : days == 21 ? '3 tuần' : '1 tháng'}',
                  style: TextStyle(
                    color:
                        selected ? AppColors.accentYellow : AppColors.textMain,
                    fontWeight: FontWeight.w800,
                    fontSize: 12,
                  ),
                ),
              ),
              if (locked) const Icon(Icons.lock, size: 16),
            ],
          ),
        ),
      ),
    );
  }
}

class _BmiStrip extends StatelessWidget {
  const _BmiStrip({required this.bmi, required this.category});

  final double bmi;
  final String category;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.bgInput,
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Text(
            bmi.toStringAsFixed(1),
            style: const TextStyle(
              color: AppColors.accentYellow,
              fontSize: 26,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(width: 12),
          Text(category, style: const TextStyle(fontWeight: FontWeight.w900)),
          const Spacer(),
          const Text('BMI', style: TextStyle(color: AppColors.textMuted)),
        ],
      ),
    );
  }
}

class _DayBadge extends StatelessWidget {
  const _DayBadge({
    required this.label,
    required this.done,
    required this.locked,
  });

  final String label;
  final bool done;
  final bool locked;

  @override
  Widget build(BuildContext context) {
    final color = locked
        ? AppColors.success
        : done
            ? AppColors.accentYellow
            : AppColors.accentPurple;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        locked ? '$label · Khóa' : label,
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.w900,
          fontSize: 11,
        ),
      ),
    );
  }
}

class _DayNutritionStrip extends StatelessWidget {
  const _DayNutritionStrip({required this.day});

  final Map<String, dynamic> day;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        if (day['target_calories'] != null)
          _MetricPill(
              Icons.local_fire_department, '${day['target_calories']} kcal'),
        if (day['target_protein'] != null)
          _MetricPill(
              Icons.egg_alt_outlined, '${day['target_protein']}g protein'),
        if (day['target_carbs'] != null)
          _MetricPill(Icons.rice_bowl_outlined, '${day['target_carbs']}g carb'),
        if (day['target_fat'] != null)
          _MetricPill(Icons.water_drop_outlined, '${day['target_fat']}g fat'),
      ],
    );
  }
}

class _MetricPill extends StatelessWidget {
  const _MetricPill(this.icon, this.label);

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.bgInput,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 15, color: AppColors.accentYellow),
          const SizedBox(width: 5),
          Text(label, style: const TextStyle(fontSize: 12)),
        ],
      ),
    );
  }
}

class _ExerciseRow extends StatelessWidget {
  const _ExerciseRow({
    required this.exercise,
    required this.draft,
    required this.locked,
    required this.onComplete,
    required this.onDetail,
  });

  final Map<String, dynamic> exercise;
  final bool draft;
  final bool locked;
  final VoidCallback onComplete;
  final VoidCallback onDetail;

  @override
  Widget build(BuildContext context) {
    final done = exercise['completed'] == true;
    final name = exercise['name_vi']?.toString().isNotEmpty == true
        ? exercise['name_vi'].toString()
        : (exercise['name'] ?? 'Bài tập').toString();
    final images = exerciseImagesFrom(exercise);
    final image = images.isEmpty ? '' : images.first.url;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: done
            ? AppColors.success.withValues(alpha: 0.07)
            : AppColors.bgInput,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: done
              ? AppColors.success.withValues(alpha: 0.4)
              : AppColors.border,
        ),
      ),
      child: Row(
        children: [
          Icon(
            done ? Icons.check_circle : Icons.circle_outlined,
            color: done ? AppColors.success : AppColors.textMuted,
          ),
          const SizedBox(width: 10),
          SizedBox(
            width: 54,
            height: 54,
            child: ExerciseImageView(
              url: image,
              icon: '${exercise['icon'] ?? '🏋️'}',
              borderRadius: BorderRadius.circular(8),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: InkWell(
              onTap: onDetail,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(name,
                      style: const TextStyle(fontWeight: FontWeight.w900)),
                  const SizedBox(height: 4),
                  Text(
                    '${exercise['sets'] ?? '--'} sets · ${exercise['reps'] ?? '--'} reps · ${exercise['muscle'] ?? ''}',
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        color: AppColors.textMuted, fontSize: 12),
                  ),
                ],
              ),
            ),
          ),
          IconButton(
            tooltip: 'Chi tiết',
            onPressed: onDetail,
            icon: const Icon(Icons.info_outline),
          ),
          if (!draft && !locked)
            FilledButton.tonal(
              onPressed: done ? null : onComplete,
              child: const Text('Xong'),
            ),
        ],
      ),
    );
  }
}

class _RestDayBox extends StatelessWidget {
  const _RestDayBox({
    required this.completed,
    required this.draft,
    required this.locked,
    required this.onComplete,
  });

  final bool completed;
  final bool draft;
  final bool locked;
  final VoidCallback onComplete;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.bgInput,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Icon(
            completed ? Icons.check_circle : Icons.self_improvement,
            color: completed ? AppColors.success : AppColors.accentPurple,
          ),
          const SizedBox(width: 10),
          const Expanded(
            child: Text(
              'Ngày nghỉ phục hồi. Ưu tiên ngủ đủ, đi bộ nhẹ và giữ protein.',
              style: TextStyle(color: AppColors.textMuted, height: 1.35),
            ),
          ),
          if (!draft && !locked)
            FilledButton.tonal(
              onPressed: completed ? null : onComplete,
              child: const Text('Xong'),
            ),
        ],
      ),
    );
  }
}

class _LockedMessage extends StatelessWidget {
  const _LockedMessage({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.success.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.success.withValues(alpha: 0.3)),
      ),
      child: Text(text, style: const TextStyle(color: AppColors.success)),
    );
  }
}

class _MacroProgress extends StatelessWidget {
  const _MacroProgress({
    required this.label,
    required this.value,
    required this.target,
    required this.unit,
    required this.color,
  });

  final String label;
  final double value;
  final double target;
  final String unit;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final pct = target <= 0 ? 0.0 : (value / target).clamp(0.0, 1.0);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(label,
                  style: const TextStyle(fontWeight: FontWeight.w800)),
            ),
            Text(
              '${value.toStringAsFixed(0)} / ${target.toStringAsFixed(0)} $unit',
              style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
            ),
          ],
        ),
        const SizedBox(height: 6),
        LinearProgressIndicator(
          value: pct,
          color: color,
          backgroundColor: AppColors.bgInput,
        ),
      ],
    );
  }
}

class _ExerciseDetailSheet extends StatelessWidget {
  const _ExerciseDetailSheet({required this.exercise});

  final Map<String, dynamic> exercise;

  @override
  Widget build(BuildContext context) {
    final steps =
        exercise['steps'] is List ? exercise['steps'] as List : const [];
    final tips = exercise['tips'] is List ? exercise['tips'] as List : const [];
    final name = exercise['name_vi']?.toString().isNotEmpty == true
        ? exercise['name_vi'].toString()
        : (exercise['name'] ?? 'Bài tập').toString();
    final images = exerciseImagesFrom(exercise);
    return Container(
      height: MediaQuery.of(context).size.height * 0.86,
      padding: const EdgeInsets.fromLTRB(20, 14, 20, 20),
      decoration: const BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
      ),
      child: SafeArea(
        top: false,
        child: ListView(
          children: [
            SizedBox(
              height: 190,
              child: _PlanExerciseImages(
                images: images,
                icon: '${exercise['icon'] ?? '🏋️'}',
              ),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: Text(
                    name,
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _MetricPill(
                    Icons.fitness_center, '${exercise['muscle'] ?? '--'}'),
                _MetricPill(Icons.repeat, '${exercise['sets'] ?? '--'} sets'),
                _MetricPill(
                    Icons.timer_outlined, '${exercise['rest'] ?? '--'}s nghỉ'),
              ],
            ),
            const SizedBox(height: 18),
            const SectionHeading(title: 'Hướng dẫn'),
            const SizedBox(height: 10),
            if (steps.isEmpty)
              const Text('Chưa có hướng dẫn.',
                  style: TextStyle(color: AppColors.textMuted))
            else
              ...steps.asMap().entries.map(
                    (entry) => Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: AppCard(
                        padding: const EdgeInsets.all(12),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '${entry.key + 1}'.padLeft(2, '0'),
                              style: const TextStyle(
                                color: AppColors.accentYellow,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                '${entry.value}',
                                style: const TextStyle(height: 1.45),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
            const SizedBox(height: 8),
            const SectionHeading(title: 'Lưu ý'),
            const SizedBox(height: 10),
            if (tips.isEmpty)
              const Text('Không có lưu ý.',
                  style: TextStyle(color: AppColors.textMuted))
            else
              ...tips.map(
                (tip) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.bolt,
                          size: 18, color: AppColors.accentYellow),
                      const SizedBox(width: 8),
                      Expanded(child: Text('$tip')),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _PlanExerciseImages extends StatelessWidget {
  const _PlanExerciseImages({required this.images, required this.icon});

  final List<ExerciseImageItem> images;
  final String icon;

  @override
  Widget build(BuildContext context) {
    if (images.isEmpty) {
      return ExerciseImageView(
        url: '',
        icon: icon,
        borderRadius: BorderRadius.circular(8),
      );
    }
    return ListView.separated(
      scrollDirection: Axis.horizontal,
      itemCount: images.length,
      separatorBuilder: (_, __) => const SizedBox(width: 10),
      itemBuilder: (context, index) {
        final item = images[index];
        return SizedBox(
          width: images.length == 1
              ? MediaQuery.sizeOf(context).width - 40
              : MediaQuery.sizeOf(context).width * 0.68,
          child: Stack(
            children: [
              Positioned.fill(
                child: ExerciseImageView(
                  url: item.url,
                  icon: icon,
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              Positioned(
                left: 10,
                bottom: 10,
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: Colors.black.withValues(alpha: 0.58),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    item.label,
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
