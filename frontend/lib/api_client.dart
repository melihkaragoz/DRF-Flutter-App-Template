import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiClient {
  static const _storage = FlutterSecureStorage();
  
  // Base URL logic: Android emulator uses 10.0.2.2, others use 127.0.0.1
  static String get baseUrl {
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000';
    } else {
      return 'http://127.0.0.1:8000';
    }
  }

  // Register a new user
  static Future<Map<String, dynamic>> register({
    required String username,
    required String password,
    String? email,
  }) async {
    final url = Uri.parse('$baseUrl/api/users/register/');
    
    final body = {
      'username': username,
      'password': password,
      if (email != null && email.isNotEmpty) 'email': email,
    };

    try {
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      );

      final data = jsonDecode(response.body);
      
      if (response.statusCode == 201) {
        return {'success': true, 'data': data};
      } else {
        return {'success': false, 'error': data};
      }
    } catch (e) {
      return {'success': false, 'error': 'Network error: $e'};
    }
  }

  // Login user and store tokens
  static Future<Map<String, dynamic>> login({
    required String username,
    required String password,
  }) async {
    final url = Uri.parse('$baseUrl/api/auth/jwt/create/');
    
    final body = {
      'username': username,
      'password': password,
    };

    try {
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      );

      final data = jsonDecode(response.body);
      
      if (response.statusCode == 200) {
        // Store tokens securely
        await _storage.write(key: 'access_token', value: data['access']);
        await _storage.write(key: 'refresh_token', value: data['refresh']);
        
        return {'success': true, 'data': data};
      } else {
        return {'success': false, 'error': data};
      }
    } catch (e) {
      return {'success': false, 'error': 'Network error: $e'};
    }
  }

  // Get user profile
  static Future<Map<String, dynamic>> getProfile() async {
    final accessToken = await _storage.read(key: 'access_token');
    
    if (accessToken == null) {
      return {'success': false, 'error': 'No access token found'};
    }

    final url = Uri.parse('$baseUrl/api/users/me/');
    
    try {
      final response = await http.get(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $accessToken',
        },
      );

      final data = jsonDecode(response.body);
      
      if (response.statusCode == 200) {
        return {'success': true, 'data': data};
      } else if (response.statusCode == 401) {
        // Try to refresh token
        final refreshResult = await _refreshToken();
        if (refreshResult['success']) {
          // Retry the request with new token
          return await getProfile();
        } else {
          // Refresh failed, user needs to login again
          await logout();
          return {'success': false, 'error': 'Authentication expired'};
        }
      } else {
        return {'success': false, 'error': data};
      }
    } catch (e) {
      return {'success': false, 'error': 'Network error: $e'};
    }
  }

  // Refresh access token
  static Future<Map<String, dynamic>> _refreshToken() async {
    final refreshToken = await _storage.read(key: 'refresh_token');
    
    if (refreshToken == null) {
      return {'success': false, 'error': 'No refresh token found'};
    }

    final url = Uri.parse('$baseUrl/api/auth/jwt/refresh/');
    
    try {
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh': refreshToken}),
      );

      final data = jsonDecode(response.body);
      
      if (response.statusCode == 200) {
        // Store new access token
        await _storage.write(key: 'access_token', value: data['access']);
        return {'success': true, 'data': data};
      } else {
        return {'success': false, 'error': data};
      }
    } catch (e) {
      return {'success': false, 'error': 'Network error: $e'};
    }
  }

  // Logout user (clear stored tokens)
  static Future<void> logout() async {
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
  }

  // Check if user is logged in
  static Future<bool> isLoggedIn() async {
    final accessToken = await _storage.read(key: 'access_token');
    return accessToken != null;
  }
}
