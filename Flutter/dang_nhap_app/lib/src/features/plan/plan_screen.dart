import 'package:flutter/material.dart';

import '../../core/api_service.dart';
import '../../core/app_colors.dart';
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

  String _goal = 'Tăng cơ';
  String _level = 'Trung bình';
  String _equipment = 'Phòng Gym đầy đủ';
  int _duration = 7;
  bool _premium = false;
  bool _loading = false;
  Map<String, dynamic>? _activePlan;
  Map<String, dynamic>? _draftPlan;
  String? _activePlanId;

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
    super.dispose();
  }

  Future<void> _loadInitial() async {
    setState(() => _loading = true);
    final results = await Future.wait([
      _api.get('/api/payment/status/${widget.user.id}'),
      _api.getPlanAi('/api/get-active-plan?userId=${widget.user.id}'),
      _api.get('/api/plans/active/${widget.user.id}'),
    ]);
    if (!mounted) return;
    final pay = _api.mapFrom(results[0].body);
    final aiPlan = _api.mapFrom(results[1].body);
    final flaskPlan = _api.mapFrom(results[2].body);
    setState(() {
      _premium = pay['isPremium'] == true ||
          widget.user.isPremium ||
          widget.user.isAdmin;
      if (results[1].ok && aiPlan.isNotEmpty) {
        _activePlan = _normalizeAiActivePlan(aiPlan);
        _activePlanId =
            (_activePlan?['id'] ?? _activePlan?['_id'] ?? aiPlan['plan_id'])
                ?.toString();
      } else if (results[2].ok && flaskPlan.isNotEmpty) {
        _activePlan = _normalizeFlaskPlan(flaskPlan);
        _activePlanId = (_activePlan?['id'] ?? flaskPlan['id'])?.toString();
      }
      _loading = false;
    });
  }

  Map<String, dynamic> _normalizeAiActivePlan(Map<String, dynamic> body) {
    final plan = body['plan_data'] is Map
        ? Map<String, dynamic>.from(body['plan_data'] as Map)
        : body;
    plan['id'] = body['plan_id'] ?? body['id'] ?? plan['id'];
    return plan;
  }

  Map<String, dynamic> _normalizeFlaskPlan(Map<String, dynamic> plan) {
    final days = plan['daily_progress'] is List
        ? plan['daily_progress'] as List
        : const [];
    return {
      ...plan,
      'plan_name': plan['title'] ?? 'Lộ trình đang thực hiện',
      'duration_days': days.length,
      'days': days.map((day) {
        final d =
            day is Map ? Map<String, dynamic>.from(day) : <String, dynamic>{};
        return {
          'day_number': d['day_number'],
          'focus': d['focus'],
          'completed': d['completed'],
          'exercises': d['exercises'] ?? const [],
        };
      }).toList(),
    };
  }

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

  Future<void> _generatePlan() async {
    final h = double.tryParse(_height.text.trim());
    final w = double.tryParse(_weight.text.trim());
    final a = int.tryParse(_age.text.trim());
    if (h == null || w == null || a == null) {
      showAppSnack(context, 'Vui lòng nhập chiều cao, cân nặng và tuổi.',
          error: true);
      return;
    }

    setState(() => _loading = true);
    final result = await _api.postPlanAi('/api/generate-plan', {
      'goal': _goal,
      'level': _level,
      'equipment': _equipment,
      'userInfo': _note.text.trim(),
      'height': h,
      'weight': w,
      'age': a,
      'duration': _duration,
    });
    if (!mounted) return;
    setState(() => _loading = false);

    if (!result.ok) {
      showAppSnack(context, result.message ?? 'Không tạo được lộ trình AI.',
          error: true);
      return;
    }
    final body = _api.mapFrom(result.body);
    final plan = body['plan_data'] is Map
        ? Map<String, dynamic>.from(body['plan_data'] as Map)
        : body;
    setState(() => _draftPlan = plan);
    showAppSnack(context, 'Đã tạo bản nháp lộ trình.');
  }

  Future<void> _saveDraft() async {
    final plan = _draftPlan;
    if (plan == null) return;
    setState(() => _loading = true);
    final result = await _api.postPlanAi('/api/save-plan', {
      'plan_data': plan,
      'userId': widget.user.id,
      'height': _height.text.trim(),
      'weight': _weight.text.trim(),
      'age': _age.text.trim(),
    });
    if (!mounted) return;
    setState(() => _loading = false);
    if (result.ok && (_api.mapFrom(result.body)['success'] != false)) {
      final body = _api.mapFrom(result.body);
      setState(() {
        _activePlan = plan;
        _activePlanId = body['plan_id']?.toString();
        _draftPlan = null;
      });
      showAppSnack(context, 'Lộ trình đã kích hoạt.');
    } else {
      showAppSnack(context, result.message ?? 'Không lưu được lộ trình.',
          error: true);
    }
  }

  Future<void> _toggleFlaskDay(int index, bool current) async {
    if (_activePlanId == null) return;
    final result =
        await _api.post('/api/plans/update_progress/$_activePlanId', {
      'day_index': index,
      'is_completed': !current,
    });
    if (!mounted) return;
    showAppSnack(context, result.message ?? 'Đã cập nhật tiến độ.',
        error: !result.ok);
    _loadInitial();
  }

  @override
  Widget build(BuildContext context) {
    final showingPlan = _draftPlan ?? _activePlan;
    return Stack(
      children: [
        const Positioned.fill(child: GridBackground()),
        SafeArea(
          child: RefreshIndicator(
            onRefresh: _loadInitial,
            child: ListView(
              padding: const EdgeInsets.only(bottom: 92),
              children: [
                ScreenHeader(
                  title: _activePlan == null
                      ? 'Lộ trình cá nhân'
                      : 'Lộ trình đang chạy',
                  subtitle: _activePlan == null
                      ? 'Điền thông số để AI thiết kế lịch tập cá nhân hóa.'
                      : 'Theo dõi tiến độ từng ngày và từng bài tập.',
                  trailing: _loading
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(strokeWidth: 2))
                      : null,
                ),
                if (_activePlan == null) _buildPlanForm(),
                if (showingPlan == null)
                  const Padding(
                    padding: EdgeInsets.all(20),
                    child: AppCard(
                      child: Text('Chưa có dữ liệu lộ trình.',
                          style: TextStyle(color: AppColors.textMuted)),
                    ),
                  )
                else
                  _PlanResult(
                    plan: showingPlan,
                    draft: _draftPlan != null,
                    activePlanId: _activePlanId,
                    onSaveDraft: _saveDraft,
                    onToggleDay: _toggleFlaskDay,
                  ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildPlanForm() {
    final bmi = _bmi;
    final canLong = _premium;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 18),
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Khởi tạo lộ trình',
                style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w900,
                    color: AppColors.accentYellow)),
            const SizedBox(height: 16),
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
              onChanged: (v) => setState(() => _goal = v),
            ),
            const SizedBox(height: 12),
            _SelectField(
              label: 'Kinh nghiệm tập luyện',
              value: _level,
              values: const ['Người mới', 'Trung bình', 'Kỳ cựu'],
              onChanged: (v) => setState(() => _level = v),
            ),
            const SizedBox(height: 12),
            _SelectField(
              label: 'Thiết bị sẵn có',
              value: _equipment,
              values: const [
                'Phòng Gym đầy đủ',
                'Tại nhà không tạ',
                'Chỉ có tạ đơn'
              ],
              onChanged: (v) => setState(() => _equipment = v),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                    child: AppTextField(
                        controller: _height,
                        label: 'Chiều cao',
                        hint: '170',
                        keyboardType: TextInputType.number,
                        onChanged: (_) => setState(() {}))),
                const SizedBox(width: 8),
                Expanded(
                    child: AppTextField(
                        controller: _weight,
                        label: 'Cân nặng',
                        hint: '65',
                        keyboardType: TextInputType.number,
                        onChanged: (_) => setState(() {}))),
                const SizedBox(width: 8),
                Expanded(
                    child: AppTextField(
                        controller: _age,
                        label: 'Tuổi',
                        hint: '24',
                        keyboardType: TextInputType.number)),
              ],
            ),
            if (bmi != null) ...[
              const SizedBox(height: 10),
              AppCard(
                padding: const EdgeInsets.all(12),
                child: Row(
                  children: [
                    Text(bmi.toStringAsFixed(1),
                        style: const TextStyle(
                            fontSize: 28,
                            fontWeight: FontWeight.w900,
                            color: AppColors.accentYellow)),
                    const SizedBox(width: 12),
                    Text(_bmiCategory(bmi),
                        style: const TextStyle(fontWeight: FontWeight.w900)),
                    const Spacer(),
                    const Text('BMI',
                        style: TextStyle(color: AppColors.textMuted)),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 14),
            const Text('Độ dài lộ trình',
                style: TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 12,
                    fontWeight: FontWeight.w900)),
            const SizedBox(height: 8),
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisSpacing: 8,
              mainAxisSpacing: 8,
              childAspectRatio: 2.4,
              children: [
                _DurationButton(
                    days: 7,
                    selected: _duration == 7,
                    locked: false,
                    onTap: () => setState(() => _duration = 7)),
                _DurationButton(
                    days: 14,
                    selected: _duration == 14,
                    locked: false,
                    onTap: () => setState(() => _duration = 14)),
                _DurationButton(
                    days: 21,
                    selected: _duration == 21,
                    locked: !canLong,
                    onTap: () => setState(() => _duration = 21)),
                _DurationButton(
                    days: 30,
                    selected: _duration == 30,
                    locked: !canLong,
                    onTap: () => setState(() => _duration = 30)),
              ],
            ),
            if (!canLong) ...[
              const SizedBox(height: 10),
              const Text('Nâng cấp Premium để mở khóa lộ trình 21 và 30 ngày.',
                  style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
            ],
            const SizedBox(height: 14),
            AppTextField(
                controller: _note,
                label: 'Tình trạng sức khỏe / Ghi chú',
                hint: 'Ví dụ: đau lưng, rảnh 45 phút/ngày...',
                maxLines: 3),
            const SizedBox(height: 16),
            PrimaryButton(
                label: 'Tạo lộ trình bằng AI',
                loading: _loading,
                onPressed: _generatePlan),
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
  });

  final String label;
  final String value;
  final List<String> values;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style: const TextStyle(
                color: AppColors.textMuted,
                fontSize: 12,
                fontWeight: FontWeight.w900)),
        const SizedBox(height: 7),
        DropdownButtonFormField<String>(
          initialValue: value,
          dropdownColor: AppColors.bgCard,
          decoration: InputDecoration(
            filled: true,
            fillColor: AppColors.bgInput,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
          ),
          items: values
              .map((v) => DropdownMenuItem(value: v, child: Text(v)))
              .toList(),
          onChanged: (v) {
            if (v != null) onChanged(v);
          },
        ),
      ],
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
      borderRadius: BorderRadius.circular(12),
      child: Opacity(
        opacity: locked ? 0.42 : 1,
        child: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: selected
                ? AppColors.accentYellow.withValues(alpha: 0.1)
                : AppColors.bgInput,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
                color: selected ? AppColors.accentYellow : AppColors.border),
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                    '$days ngày\n${days == 7 ? 'Tuần đầu' : days == 14 ? '2 tuần' : days == 21 ? '3 tuần' : '1 tháng'}',
                    style: TextStyle(
                        color: selected
                            ? AppColors.accentYellow
                            : AppColors.textMain,
                        fontWeight: FontWeight.w800,
                        fontSize: 12)),
              ),
              if (locked) const Icon(Icons.lock, size: 16),
            ],
          ),
        ),
      ),
    );
  }
}

class _PlanResult extends StatelessWidget {
  const _PlanResult({
    required this.plan,
    required this.draft,
    required this.activePlanId,
    required this.onSaveDraft,
    required this.onToggleDay,
  });

  final Map<String, dynamic> plan;
  final bool draft;
  final String? activePlanId;
  final VoidCallback onSaveDraft;
  final Future<void> Function(int index, bool current) onToggleDay;

  @override
  Widget build(BuildContext context) {
    final days = plan['days'] is List ? plan['days'] as List : const [];
    final done = days.where((d) => d is Map && d['completed'] == true).length;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        children: [
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${plan['plan_name'] ?? plan['title'] ?? 'Lộ trình AI'}',
                    style: const TextStyle(
                        fontSize: 22, fontWeight: FontWeight.w900)),
                const SizedBox(height: 6),
                Text(
                    '${plan['goal'] ?? ''} · ${plan['duration_days'] ?? days.length} ngày',
                    style: const TextStyle(color: AppColors.textMuted)),
                const SizedBox(height: 14),
                LinearProgressIndicator(
                  value: days.isEmpty ? 0 : done / days.length,
                  color: AppColors.accentYellow,
                  backgroundColor: AppColors.bgInput,
                ),
                const SizedBox(height: 8),
                Text('$done / ${days.length} ngày hoàn thành',
                    style: const TextStyle(color: AppColors.textMuted)),
                if (draft) ...[
                  const SizedBox(height: 14),
                  PrimaryButton(
                      label: 'Áp dụng lộ trình này', onPressed: onSaveDraft),
                ],
              ],
            ),
          ),
          const SizedBox(height: 14),
          if (days.isEmpty)
            const AppCard(
                child: Text('Plan chưa có danh sách ngày.',
                    style: TextStyle(color: AppColors.textMuted)))
          else
            ...days.asMap().entries.map((entry) {
              final index = entry.key;
              final day = entry.value is Map
                  ? Map<String, dynamic>.from(entry.value as Map)
                  : <String, dynamic>{};
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _DayCard(
                  day: day,
                  index: index,
                  draft: draft,
                  onToggle: (current) => onToggleDay(index, current),
                ),
              );
            }),
        ],
      ),
    );
  }
}

class _DayCard extends StatelessWidget {
  const _DayCard({
    required this.day,
    required this.index,
    required this.draft,
    required this.onToggle,
  });

  final Map<String, dynamic> day;
  final int index;
  final bool draft;
  final ValueChanged<bool> onToggle;

  @override
  Widget build(BuildContext context) {
    final exercises =
        day['exercises'] is List ? day['exercises'] as List : const [];
    final completed = day['completed'] == true;
    final isRest = day['is_rest'] == true || exercises.isEmpty;
    final targetCal = day['target_calories'] ?? day['calories'];
    final targetProtein = day['target_protein'] ?? day['protein'];
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.accentYellow.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(7),
                ),
                child: Text('NGÀY ${day['day_number'] ?? index + 1}',
                    style: const TextStyle(
                        color: AppColors.accentYellow,
                        fontSize: 11,
                        fontWeight: FontWeight.w900)),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                    '${day['focus'] ?? day['title'] ?? (isRest ? 'Nghỉ phục hồi' : 'Tập luyện')}',
                    style: const TextStyle(fontWeight: FontWeight.w900)),
              ),
              if (!draft)
                Checkbox(
                  value: completed,
                  onChanged: (_) => onToggle(completed),
                ),
            ],
          ),
          if (targetCal != null || targetProtein != null) ...[
            const SizedBox(height: 10),
            Row(
              children: [
                if (targetCal != null)
                  Expanded(
                      child: _MiniMetric(
                          icon: Icons.local_fire_department,
                          value: '$targetCal kcal')),
                if (targetProtein != null)
                  Expanded(
                      child: _MiniMetric(
                          icon: Icons.egg_alt_outlined,
                          value: '${targetProtein}g protein')),
              ],
            ),
          ],
          const SizedBox(height: 12),
          if (isRest)
            const Text('Ngày nghỉ phục hồi. Tập trung ngủ đủ và dinh dưỡng.',
                style: TextStyle(color: AppColors.textMuted))
          else
            ...exercises.map((ex) {
              final e =
                  ex is Map ? Map<String, dynamic>.from(ex) : {'name': ex};
              return Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.bgInput,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: Row(
                    children: [
                      Icon(
                          e['completed'] == true
                              ? Icons.check_circle
                              : Icons.circle_outlined,
                          color: e['completed'] == true
                              ? AppColors.success
                              : AppColors.textMuted),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('${e['name'] ?? 'Bài tập'}',
                                style: const TextStyle(
                                    fontWeight: FontWeight.w800)),
                            Text(
                                '${e['sets'] ?? ''} sets · ${e['reps'] ?? ''} reps · ${e['muscle'] ?? ''}',
                                style: const TextStyle(
                                    color: AppColors.textMuted, fontSize: 12)),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }),
        ],
      ),
    );
  }
}

class _MiniMetric extends StatelessWidget {
  const _MiniMetric({required this.icon, required this.value});

  final IconData icon;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, color: AppColors.accentYellow, size: 17),
        const SizedBox(width: 6),
        Flexible(
            child: Text(value,
                style:
                    const TextStyle(fontSize: 12, color: AppColors.textMuted))),
      ],
    );
  }
}
