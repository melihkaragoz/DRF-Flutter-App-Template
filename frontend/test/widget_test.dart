// This is a basic Flutter widget test for the Rose app.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:rose/main.dart';

void main() {
  testWidgets('Rose app smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const RoseApp());

    // Verify that the splash screen shows initially
    expect(find.text('Rose'), findsOneWidget);
    expect(find.text('Simple & Secure'), findsOneWidget);

    // Wait for splash screen to complete
    await tester.pumpAndSettle(const Duration(seconds: 2));

    // After splash, should navigate to login page (since no user is logged in)
    // The login page should be visible
    expect(find.text('Welcome Back'), findsOneWidget);
    expect(find.text('Username'), findsOneWidget);
    expect(find.text('Password'), findsOneWidget);
  });

  testWidgets('Login page toggle test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const RoseApp());

    // Wait for navigation to login page
    await tester.pumpAndSettle(const Duration(seconds: 2));

    // Should start in login mode
    expect(find.text('Welcome Back'), findsOneWidget);
    expect(find.text('Login'), findsOneWidget);

    // Tap register toggle
    await tester.tap(find.text('Don\'t have an account? Register'));
    await tester.pump();

    // Should switch to register mode
    expect(find.text('Create Account'), findsOneWidget);
    expect(find.text('Register'), findsOneWidget);
    expect(find.text('Email (optional)'), findsOneWidget);

    // Tap login toggle
    await tester.tap(find.text('Already have an account? Login'));
    await tester.pump();

    // Should switch back to login mode
    expect(find.text('Welcome Back'), findsOneWidget);
    expect(find.text('Login'), findsOneWidget);
  });
}
