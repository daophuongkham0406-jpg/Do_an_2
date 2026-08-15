import 'package:dang_nhap_app/src/app.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('shows mobile auth screen', (tester) async {
    await tester.pumpWidget(const FitMeApp());

    expect(find.text('FIT ME • MOBILE'), findsOneWidget);
    expect(find.text('Đăng nhập'), findsWidgets);
  });
}
