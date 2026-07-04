import 'dart:convert';

import 'package:http/http.dart' as http;

import 'models.dart';

class BackendException implements Exception {
  BackendException(this.message);

  final String message;

  @override
  String toString() => 'BackendException: $message';
}

class BackendClient {
  BackendClient({required this.baseUrl, http.Client? httpClient})
      : _httpClient = httpClient ?? http.Client();

  final String baseUrl;
  final http.Client _httpClient;

  Future<ConversationResponse> sendConversation(ConversationRequest request) async {
    final uri = Uri.parse('$baseUrl/conversation');
    final response = await _httpClient.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(request.toJson()),
    );

    if (response.statusCode != 200) {
      throw BackendException(
        'Backend returned ${response.statusCode}: ${response.body}',
      );
    }

    return ConversationResponse.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<CurrencyLookupResponse> lookupCurrency(String imageBase64) async {
    final uri = Uri.parse('$baseUrl/currency-lookup');
    final response = await _httpClient.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'image_base64': imageBase64}),
    );

    if (response.statusCode != 200) {
      throw BackendException(
        'Backend returned ${response.statusCode}: ${response.body}',
      );
    }

    return CurrencyLookupResponse.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<ProductLookupResponse> lookupProduct(String barcode) async {
    final uri = Uri.parse('$baseUrl/product-lookup');
    final response = await _httpClient.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'barcode': barcode}),
    );

    if (response.statusCode != 200) {
      throw BackendException(
        'Backend returned ${response.statusCode}: ${response.body}',
      );
    }

    return ProductLookupResponse.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }
}
