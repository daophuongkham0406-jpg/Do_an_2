import 'package:flutter/material.dart';

import '../../core/api_service.dart';
import '../../core/app_colors.dart';
import '../admin/admin_screen.dart';
import '../exercises/exercises_screen.dart';
import '../faq/faq_screen.dart';
import '../home/home_screen.dart';
import '../plan/plan_screen.dart';
import '../profile/profile_screen.dart';

class MainShell extends StatefulWidget {
  const MainShell({
    required this.user,
    required this.onLogout,
    super.key,
  });

  final AppUser user;
  final VoidCallback onLogout;

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final pages = [
      HomeScreen(user: widget.user),
      ExercisesScreen(user: widget.user),
      PlanScreen(user: widget.user),
      ProfileScreen(user: widget.user, onLogout: widget.onLogout),
      const FaqScreen(),
      if (widget.user.isAdmin) const AdminScreen(),
    ];
    final items = [
      const NavigationDestination(
          icon: Icon(Icons.home_outlined),
          selectedIcon: Icon(Icons.home),
          label: 'Trang chủ'),
      const NavigationDestination(
          icon: Icon(Icons.fitness_center_outlined),
          selectedIcon: Icon(Icons.fitness_center),
          label: 'Bài tập'),
      const NavigationDestination(
          icon: Icon(Icons.route_outlined),
          selectedIcon: Icon(Icons.route),
          label: 'Lộ trình'),
      const NavigationDestination(
          icon: Icon(Icons.person_outline),
          selectedIcon: Icon(Icons.person),
          label: 'Hồ sơ'),
      const NavigationDestination(
          icon: Icon(Icons.help_outline),
          selectedIcon: Icon(Icons.help),
          label: 'FAQ'),
      if (widget.user.isAdmin)
        const NavigationDestination(
            icon: Icon(Icons.admin_panel_settings_outlined),
            selectedIcon: Icon(Icons.admin_panel_settings),
            label: 'Admin'),
    ];

    return Scaffold(
      body: IndexedStack(index: _index, children: pages),
      floatingActionButton: FloatingActionButton(
        backgroundColor: AppColors.accentYellow,
        foregroundColor: Colors.black,
        onPressed: () => showModalBottomSheet<void>(
          context: context,
          isScrollControlled: true,
          backgroundColor: Colors.transparent,
          builder: (_) => const ChatCoachSheet(),
        ),
        child: const Icon(Icons.bolt),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (value) => setState(() => _index = value),
        backgroundColor: AppColors.bgCard,
        indicatorColor: AppColors.accentPurple,
        labelBehavior: NavigationDestinationLabelBehavior.onlyShowSelected,
        destinations: items,
      ),
    );
  }
}

class ChatCoachSheet extends StatefulWidget {
  const ChatCoachSheet({super.key});

  @override
  State<ChatCoachSheet> createState() => _ChatCoachSheetState();
}

class _ChatCoachSheetState extends State<ChatCoachSheet> {
  final _api = const ApiService();
  final _input = TextEditingController();
  final _messages = <_ChatMessage>[
    const _ChatMessage(
      text:
          'Chào bạn! Mình là AI HLV của FIT ME. Hôm nay bạn cần tư vấn bài tập hay chế độ ăn uống gì không?',
      mine: false,
    ),
  ];
  bool _loading = false;

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  Future<void> _send([String? preset]) async {
    final text = (preset ?? _input.text).trim();
    if (text.isEmpty || _loading) return;
    _input.clear();
    setState(() {
      _messages.add(_ChatMessage(text: text, mine: true));
      _loading = true;
    });

    final result = await _api.postAi('/api/chat', {'message': text});
    if (!mounted) return;
    final body = _api.mapFrom(result.body);
    setState(() {
      _messages.add(_ChatMessage(
        text: result.ok
            ? (body['reply'] ?? 'Không có phản hồi.').toString()
            : (result.message ?? 'Lỗi kết nối máy chủ AI cổng 5002.'),
        mine: false,
      ));
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding:
          EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Container(
        height: MediaQuery.of(context).size.height * 0.82,
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
        decoration: const BoxDecoration(
          color: AppColors.bgCard,
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: SafeArea(
          top: false,
          child: Column(
            children: [
              Row(
                children: [
                  const Expanded(
                    child: Text(
                      'AI Huấn luyện viên',
                      style:
                          TextStyle(fontSize: 22, fontWeight: FontWeight.w900),
                    ),
                  ),
                  IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(Icons.close)),
                ],
              ),
              SizedBox(
                height: 40,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  children: [
                    _SuggestionChip('Lên lộ trình Clean Bulk', _send),
                    _SuggestionChip('Mục tiêu tăng 3kg cơ', _send),
                    _SuggestionChip('Bài tập ngực hôm nay', _send),
                  ],
                ),
              ),
              const SizedBox(height: 10),
              Expanded(
                child: ListView.builder(
                  itemCount: _messages.length + (_loading ? 1 : 0),
                  itemBuilder: (context, index) {
                    if (index == _messages.length) {
                      return const Align(
                        alignment: Alignment.centerLeft,
                        child: Padding(
                          padding: EdgeInsets.all(8),
                          child: Text('HLV đang suy nghĩ...',
                              style: TextStyle(color: AppColors.textMuted)),
                        ),
                      );
                    }
                    final msg = _messages[index];
                    return Align(
                      alignment: msg.mine
                          ? Alignment.centerRight
                          : Alignment.centerLeft,
                      child: Container(
                        margin: const EdgeInsets.symmetric(vertical: 5),
                        padding: const EdgeInsets.all(12),
                        constraints: BoxConstraints(
                            maxWidth: MediaQuery.of(context).size.width * 0.76),
                        decoration: BoxDecoration(
                          color: msg.mine
                              ? AppColors.accentPurple
                              : AppColors.bgInput,
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: Text(msg.text),
                      ),
                    );
                  },
                ),
              ),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _input,
                      decoration: InputDecoration(
                        hintText: 'Nhập câu hỏi...',
                        filled: true,
                        fillColor: AppColors.bgInput,
                        border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(14)),
                      ),
                      onSubmitted: (_) => _send(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed: _send,
                    icon: const Icon(Icons.send),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ChatMessage {
  const _ChatMessage({required this.text, required this.mine});

  final String text;
  final bool mine;
}

class _SuggestionChip extends StatelessWidget {
  const _SuggestionChip(this.text, this.onTap);

  final String text;
  final ValueChanged<String> onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ActionChip(
        label: Text(text),
        onPressed: () => onTap(text),
      ),
    );
  }
}
