import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;

import 'package:be_my_eye/features/conversation/media_services.dart';

void main() {
  test('compressImageBytes resizes a large image down to the max dimension', () {
    final large = img.Image(width: 2000, height: 1000);
    final rawBytes = Uint8List.fromList(img.encodePng(large));

    final compressed = compressImageBytes(rawBytes, maxDimension: 1024, jpegQuality: 70);

    final decoded = img.decodeImage(compressed);
    expect(decoded, isNotNull);
    expect(decoded!.width, 1024);
    expect(decoded.height, 512);
  });

  test('compressImageBytes leaves a small image at its original size', () {
    final small = img.Image(width: 200, height: 100);
    final rawBytes = Uint8List.fromList(img.encodePng(small));

    final compressed = compressImageBytes(rawBytes, maxDimension: 1024, jpegQuality: 70);

    final decoded = img.decodeImage(compressed);
    expect(decoded!.width, 200);
    expect(decoded.height, 100);
  });

  test('compressImageBytes encodes output as JPEG', () {
    final image = img.Image(width: 100, height: 100);
    final rawBytes = Uint8List.fromList(img.encodePng(image));

    final compressed = compressImageBytes(rawBytes);

    // JPEG magic bytes: 0xFF 0xD8
    expect(compressed[0], 0xFF);
    expect(compressed[1], 0xD8);
  });
}
