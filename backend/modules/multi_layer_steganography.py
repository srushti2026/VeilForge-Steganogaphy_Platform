#!/usr/bin/env python3
"""
FIXED MULTI-LAYER STEGANOGRAPHY MODULE - RECURSIVE LAYERED EMBEDDING
Supports true multi-level embedding where each layer contains all previous layers
"""

import os
import json
import hashlib
import base64
import struct
import zipfile
import tempfile
import uuid
from typing import Dict, Any, Optional, Union, Tuple, List
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

def _is_likely_text_content(data):
    """Check if data is likely to be text content that can be safely decoded"""
    if not data:
        return False
    
    try:
        # Try to decode a sample to see if it's text
        sample = data[:min(1000, len(data))]
        decoded = sample.decode('utf-8', errors='strict')
        
        # Check if it contains mostly printable characters
        printable_chars = sum(1 for c in decoded if c.isprintable() or c.isspace())
        ratio = printable_chars / len(decoded) if decoded else 0
        
        return ratio > 0.8  # 80% printable characters
    except (UnicodeDecodeError, UnicodeError):
        return False

def detect_filename_from_content(data):
    """Detect appropriate filename and extension based on file content"""
    if not data:
        return "extracted_file.bin"
    
    # Convert to bytes if it's a string
    if isinstance(data, str):
        try:
            data_bytes = data.encode('utf-8')
        except:
            return "extracted_file.txt"
    else:
        data_bytes = data
    
    # Check for common file signatures
    if data_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return "extracted_image.png"
    elif data_bytes.startswith(b'\xFF\xD8\xFF'):
        return "extracted_image.jpg"
    elif data_bytes.startswith(b'GIF8'):
        return "extracted_image.gif"
    elif data_bytes.startswith(b'%PDF'):
        return "extracted_document.pdf"
    elif data_bytes.startswith(b'PK\x03\x04'):
        # Could be ZIP, DOCX, XLSX, etc.
        if b'word/' in data_bytes[:1024]:
            return "extracted_document.docx"
        elif b'xl/' in data_bytes[:1024]:
            return "extracted_document.xlsx"
        else:
            return "extracted_archive.zip"
    # Audio formats
    elif data_bytes.startswith(b'RIFF') and b'WAVE' in data_bytes[:20]:
        return "extracted_audio.wav"
    elif data_bytes.startswith(b'ID3') or data_bytes.startswith(b'\xFF\xFB') or data_bytes.startswith(b'\xFF\xFA'):
        return "extracted_audio.mp3"
    elif data_bytes.startswith(b'fLaC'):
        return "extracted_audio.flac"
    elif data_bytes.startswith(b'OggS'):
        return "extracted_audio.ogg"
    elif data_bytes.startswith(b'\xFF\xF1') or data_bytes.startswith(b'\xFF\xF9'):
        return "extracted_audio.aac"
    elif data_bytes.startswith(b'\x00\x00\x00\x20ftypM4A'):
        return "extracted_audio.m4a"
    elif data_bytes.startswith(b'\x30\x26\xB2\x75\x8E\x66\xCF\x11'):
        return "extracted_audio.wma"
    
    # Video formats
    elif (data_bytes.startswith(b'\x00\x00\x00\x18ftyp') or 
          data_bytes.startswith(b'\x00\x00\x00\x20ftyp')):
        # Check specific MP4 variants
        if b'mp41' in data_bytes[:50] or b'mp42' in data_bytes[:50] or b'isom' in data_bytes[:50]:
            return "extracted_video.mp4"
        elif b'M4V' in data_bytes[:50]:
            return "extracted_video.m4v"
        elif b'qt' in data_bytes[:50]:
            return "extracted_video.mov"
        else:
            return "extracted_video.mp4"  # Default to mp4
    elif data_bytes.startswith(b'RIFF') and b'AVI ' in data_bytes[:20]:
        return "extracted_video.avi"
    elif data_bytes.startswith(b'\x1A\x45\xDF\xA3'):
        return "extracted_video.mkv"
    elif data_bytes.startswith(b'\x30\x26\xB2\x75\x8E\x66\xCF\x11'):
        return "extracted_video.wmv"
    elif data_bytes.startswith(b'FLV\x01'):
        return "extracted_video.flv"
    elif data_bytes.startswith(b'\x1A\x45\xDF\xA3') and b'webm' in data_bytes[:100]:
        return "extracted_video.webm"
    else:
        # Check if it looks like text content
        try:
            if isinstance(data, str):
                return "extracted_text.txt"
            else:
                decoded = data_bytes.decode('utf-8', errors='ignore')
                if all(ord(c) < 128 or c.isspace() for c in decoded[:100]):  # ASCII-like content
                    return "extracted_text.txt"
        except:
            pass
    
    return "extracted_file.bin"

class FixedMultiLayerSteganography:
    """FIXED: True multi-layer steganography with recursive layer structure"""
    
    def __init__(self):
        # Unified magic header for all layers
        self.magic_header = b"VEILFORGE_MULTILAYER_UNIFIED_V1"
        self.end_marker = b"VEILFORGE_MULTILAYER_END_V1"
        
        # Legacy compatibility
        self.legacy_magic = b"VEILFORGE_UNIVERSAL_SAFE_V2"
        self.legacy_end = b"VEILFORGE_UNIVERSAL_END_V2"
    
    def hide_data(self, carrier_file_path: str, content_to_hide: Union[str, bytes], 
                  output_path: str, password: Optional[str] = None, 
                  is_file: bool = False, original_filename: str = None, **kwargs) -> Dict[str, Any]:
        """
        FIXED: Multi-layer hiding method that creates proper recursive structure
        Each new layer contains ALL previous layers as a complete package
        """
        
        print(f"[FIXED-MULTILAYER] Processing {os.path.basename(carrier_file_path)}")
        
        # Read carrier file (might already contain hidden layers)
        with open(carrier_file_path, 'rb') as f:
            carrier_data = f.read()
        
        # Check if this file already contains hidden data
        existing_structure = self._extract_existing_multilayer_structure(carrier_data, password)
        
        if existing_structure:
            layer_count = len(existing_structure['layers']) + 1
            print(f"[FIXED-MULTILAYER] Found existing structure with {len(existing_structure['layers'])} layers")
            print(f"[FIXED-MULTILAYER] Adding new layer #{layer_count}")
        else:
            layer_count = 1
            print(f"[FIXED-MULTILAYER] Creating first layer")
        
        # Prepare new content
        if is_file and isinstance(content_to_hide, str) and os.path.exists(content_to_hide):
            with open(content_to_hide, 'rb') as f:
                new_content = f.read()
            new_filename = original_filename or os.path.basename(content_to_hide)
        else:
            # Handle various input types safely
            if isinstance(content_to_hide, str):
                new_content = content_to_hide.encode('utf-8')
            elif isinstance(content_to_hide, bytes):
                new_content = content_to_hide
            else:
                new_content = str(content_to_hide).encode('utf-8')
            
            new_filename = original_filename or detect_filename_from_content(new_content)
        
        # Create the multilayer structure
        if existing_structure:
            # Add to existing structure
            multilayer_data = self._add_layer_to_structure(
                existing_structure, new_content, new_filename, layer_count
            )
        else:
            # Create new structure
            multilayer_data = self._create_new_multilayer_structure(
                new_content, new_filename, layer_count
            )
        
        # Get the original carrier file data (without any existing embedded data)
        if existing_structure:
            # Use the original carrier from the existing structure
            original_carrier = existing_structure['original_carrier']
        else:
            # This is the first embedding, so the current file is the original carrier
            original_carrier = carrier_data
        
        # Encrypt the complete multilayer structure if password provided
        if password:
            encrypted_data = self._encrypt_data(multilayer_data, password)
        else:
            encrypted_data = multilayer_data
        
        # Create metadata for the complete structure
        structure_metadata = {
            'version': 'fixed_multilayer_v1',
            'total_layers': layer_count,
            'encrypted': bool(password),
            'password_hash': hashlib.sha256((password or "").encode()).hexdigest() if password else None,
            'original_carrier_size': len(original_carrier),
            'structure_size': len(multilayer_data),
            'structure_checksum': hashlib.sha256(multilayer_data).hexdigest()
        }
        
        metadata_json = json.dumps(structure_metadata).encode('utf-8')
        
        # Build the final embedded file: original_carrier + embedded_structure
        embedded_structure = (
            self.magic_header +
            len(metadata_json).to_bytes(4, 'little') +
            metadata_json +
            len(encrypted_data).to_bytes(4, 'little') +
            encrypted_data +
            self.end_marker
        )
        
        # Final file = original carrier + embedded structure
        final_file = original_carrier + embedded_structure
        
        # Write to output
        with open(output_path, 'wb') as f:
            f.write(final_file)
        
        overhead = len(final_file) - len(original_carrier)
        
        print(f"[FIXED-MULTILAYER] ✅ Layer #{layer_count} added successfully")
        print(f"[FIXED-MULTILAYER] ✅ Total structure size: {len(multilayer_data)} bytes")
        print(f"[FIXED-MULTILAYER] ✅ Total overhead: {overhead} bytes")
        
        return {
            'success': True,
            'method': 'fixed_multilayer_recursive',
            'layer_number': layer_count,
            'total_layers': layer_count,
            'overhead_bytes': overhead,
            'structure_size': len(multilayer_data),
            'file_type_preserved': True
        }
    
    def _create_new_multilayer_structure(self, content: bytes, filename: str, layer_number: int) -> bytes:
        """Create a new multilayer structure with the first layer"""
        
        structure = {
            'type': 'fixed_multilayer_container',
            'version': 1,
            'created_layer': layer_number,
            'layers': [
                {
                    'layer_number': layer_number,
                    'filename': filename,
                    'content_size': len(content),
                    'content_base64': base64.b64encode(content).decode('utf-8'),
                    'checksum': hashlib.sha256(content).hexdigest(),
                    'timestamp': str(uuid.uuid4())
                }
            ]
        }
        
        return json.dumps(structure).encode('utf-8')
    
    def _add_layer_to_structure(self, existing_structure: Dict, new_content: bytes, 
                               new_filename: str, layer_number: int) -> bytes:
        """Add a new layer to existing multilayer structure"""
        
        # Add the new layer to the existing layers
        existing_structure['layers'].append({
            'layer_number': layer_number,
            'filename': new_filename,
            'content_size': len(new_content),
            'content_base64': base64.b64encode(new_content).decode('utf-8'),
            'checksum': hashlib.sha256(new_content).hexdigest(),
            'timestamp': str(uuid.uuid4())
        })
        
        # Update metadata
        existing_structure['created_layer'] = layer_number
        
        # Create a clean structure for JSON serialization (exclude non-serializable fields)
        clean_structure = {
            'type': existing_structure['type'],
            'version': existing_structure['version'],
            'created_layer': existing_structure['created_layer'],
            'layers': existing_structure['layers']
        }
        
        return json.dumps(clean_structure).encode('utf-8')
    
    def _extract_existing_multilayer_structure(self, file_data: bytes, password: Optional[str]) -> Optional[Dict]:
        """Extract existing multilayer structure from file"""
        
        # Look for our magic header
        magic_pos = file_data.find(self.magic_header)
        if magic_pos == -1:
            return None
        
        try:
            # Parse metadata
            metadata_size_pos = magic_pos + len(self.magic_header)
            metadata_size = int.from_bytes(file_data[metadata_size_pos:metadata_size_pos+4], 'little')
            
            metadata_pos = metadata_size_pos + 4
            metadata_json = file_data[metadata_pos:metadata_pos+metadata_size]
            metadata = json.loads(metadata_json.decode('utf-8'))
            
            # Check if password is required and matches
            if metadata.get('encrypted') and not password:
                print("[FIXED-MULTILAYER] Structure is encrypted but no password provided")
                return None
            elif metadata.get('password_hash') and password:
                provided_hash = hashlib.sha256(password.encode()).hexdigest()
                if metadata['password_hash'] != provided_hash:
                    print("[FIXED-MULTILAYER] Password does not match")
                    return None
            
            # Parse structure data
            data_size_pos = metadata_pos + metadata_size
            data_size = int.from_bytes(file_data[data_size_pos:data_size_pos+4], 'little')
            
            structure_pos = data_size_pos + 4
            structure_data = file_data[structure_pos:structure_pos+data_size]
            
            # Decrypt if needed
            if metadata.get('encrypted') and password:
                structure_data = self._decrypt_data(structure_data, password)
            
            # Parse the multilayer structure
            structure = json.loads(structure_data.decode('utf-8'))
            
            # Add original carrier data (everything before the magic header) - store as base64 to avoid JSON serialization issues
            structure['original_carrier'] = file_data[:magic_pos]  # Keep as bytes for internal use
            structure['metadata'] = metadata
            
            return structure
            
        except Exception as e:
            print(f"[FIXED-MULTILAYER] Error extracting existing structure: {e}")
            return None
    
    def _embed_new_layer(self, file_data: bytes, secret_data: bytes, 
                        output_path: str, password: Optional[str], 
                        filename: str, file_ext: str, layer_number: int,
                        existing_layers: List[Dict]) -> Dict[str, Any]:
        """Embed a new layer into the file"""
        
        if layer_number > 5:
            raise ValueError("Maximum 5 layers supported")
        
        # Create layer metadata
        layer_id = str(uuid.uuid4())
        password_hash = hashlib.sha256((password or "").encode()).hexdigest() if password else None
        
        # SECURITY: Add file hash to bind this layer to THIS specific file
        file_hash = hashlib.sha256(file_data).hexdigest()[:16]
        
        metadata = {
            'layer_id': layer_id,
            'layer_number': layer_number,
            'filename': filename,
            'original_size': len(secret_data),
            'encrypted': bool(password),
            'password_hash': password_hash,
            'checksum': hashlib.sha256(secret_data).hexdigest(),
            'carrier_ext': file_ext,
            'file_hash': file_hash,  # SECURITY: Bind to specific file
            'timestamp': hashlib.md5(str(layer_number).encode()).hexdigest()[:8]  # Layer identifier
        }
        
        # Encrypt if password provided
        if password:
            payload_data = self._encrypt_data(secret_data, password)
        else:
            payload_data = secret_data
        
        metadata_json = json.dumps(metadata).encode('utf-8')
        
        # Get magic headers for this layer
        magic_header = self.magic_headers[layer_number]
        end_marker = self.end_markers[layer_number]
        
        # Build new layer format
        new_layer = (
            magic_header +
            len(metadata_json).to_bytes(4, 'little') +
            metadata_json +
            len(payload_data).to_bytes(4, 'little') +
            payload_data +
            end_marker
        )
        
        # Append new layer to existing file data
        final_file = file_data + new_layer
        
        # Update layer index
        final_file = self._update_layer_index(final_file, existing_layers, metadata)
        
        # Write final file
        with open(output_path, 'wb') as f:
            f.write(final_file)
        
        overhead = len(final_file) - len(file_data)
        
        print(f"[MULTI-LAYER] ✅ Layer #{layer_number} added successfully")
        print(f"[MULTI-LAYER] ✅ Added {overhead} bytes for new layer")
        print(f"[MULTI-LAYER] ✅ Total layers: {len(existing_layers) + 1}")
        
        return {
            'success': True,
            'method': 'multi_layer_safe_append',
            'layer_number': layer_number,
            'layer_id': layer_id,
            'total_layers': len(existing_layers) + 1,
            'overhead_bytes': overhead,
            'file_type_preserved': True
        }
    
    def _update_layer_index(self, file_data: bytes, existing_layers: List[Dict], new_layer_metadata: Dict) -> bytes:
        """Update or create the layer index at the end of file"""
        
        # Remove existing index if present (but preserve all layer data)
        index_pos = file_data.find(self.layer_index_magic)
        if index_pos != -1:
            # Find the end of the index block
            index_end_pos = file_data.find(self.layer_index_end, index_pos)
            if index_end_pos != -1:
                # Remove only the index block, keep everything else
                file_data = file_data[:index_pos] + file_data[index_end_pos + len(self.layer_index_end):]
            else:
                # Fallback: truncate at index start if end marker not found
                file_data = file_data[:index_pos]
        
        # Build complete layer list
        all_layers = []
        for layer in existing_layers:
            all_layers.append({
                'layer_number': layer['layer_number'],
                'password_hash': layer.get('password_hash'),
                'magic_pos': layer['magic_pos']
            })
        
        # Add new layer info
        all_layers.append({
            'layer_number': new_layer_metadata['layer_number'],
            'password_hash': new_layer_metadata.get('password_hash'),
            'layer_id': new_layer_metadata['layer_id']
        })
        
        # Create index structure
        index_data = {
            'version': 1,
            'total_layers': len(all_layers),
            'layers': all_layers,
            'created_by': 'VeilForge_MultiLayer_V1'
        }
        
        index_json = json.dumps(index_data).encode('utf-8')
        
        # Append index
        index_block = (
            self.layer_index_magic +
            len(index_json).to_bytes(4, 'little') +
            index_json +
            self.layer_index_end
        )
        
        return file_data + index_block
    
    def extract_all_layers(self, stego_file_path: str, password: Optional[str] = None, 
                          output_dir: str = None) -> Dict[str, Any]:
        """
        FIXED: Extract all layers from multilayer structure
        Returns all layers that were embedded with the same password
        """
        
        with open(stego_file_path, 'rb') as f:
            file_data = f.read()
        
        print(f"[FIXED-MULTILAYER] Analyzing file for multilayer structure...")
        
        # Try to extract multilayer structure
        structure = self._extract_existing_multilayer_structure(file_data, password)
        
        if not structure:
            # Fallback: Try legacy extraction for backward compatibility
            legacy_result = self._try_legacy_extraction(file_data, password)
            if legacy_result:
                return legacy_result
            
            print("[FIXED-MULTILAYER] No multilayer structure found")
            return {'success': False, 'message': 'No hidden data found or incorrect password'}
        
        layers = structure.get('layers', [])
        if not layers:
            return {'success': False, 'message': 'No layers found in structure'}
        
        print(f"[FIXED-MULTILAYER] Found {len(layers)} layer(s)")
        
        # Extract all layers
        extracted_layers = []
        
        for layer in layers:
            try:
                # Decode layer content
                content_data = base64.b64decode(layer['content_base64'])
                
                # Verify checksum
                expected_checksum = layer.get('checksum')
                if expected_checksum:
                    actual_checksum = hashlib.sha256(content_data).hexdigest()
                    if actual_checksum != expected_checksum:
                        print(f"[FIXED-MULTILAYER] Warning: Checksum mismatch for layer {layer['layer_number']}")
                
                extracted_layers.append({
                    'layer_number': layer['layer_number'],
                    'filename': layer['filename'],
                    'content': content_data,
                    'size': len(content_data)
                })
                
                print(f"[FIXED-MULTILAYER] ✅ Extracted layer #{layer['layer_number']}: {layer['filename']}")
                
            except Exception as e:
                print(f"[FIXED-MULTILAYER] ⚠️ Failed to extract layer #{layer['layer_number']}: {e}")
        
        if not extracted_layers:
            return {'success': False, 'message': 'Failed to extract any layers'}
        
        # If only one layer extracted, return it directly
        if len(extracted_layers) == 1:
            layer = extracted_layers[0]
            if output_dir:
                output_path = os.path.join(output_dir, f"extracted_{layer['filename']}")
                with open(output_path, 'wb') as f:
                    f.write(layer['content'])
                layer['saved_to'] = output_path
            
            # CRITICAL FIX: Return the actual binary content for file extraction
            # Don't try to decode binary files as text - preserve the original binary data
            content_data = layer['content']
            
            # Only convert to text if it's actually text content
            try:
                # Check if it's likely text content by trying to decode a small sample
                if len(content_data) > 0 and _is_likely_text_content(content_data):
                    text_content = content_data.decode('utf-8')
                    print(f"[MULTI-LAYER] Extracted text content: {len(text_content)} characters")
                else:
                    # For binary files, return the binary content directly for processing
                    text_content = f"[Binary file: {layer['filename']}]"
                    print(f"[MULTI-LAYER] Extracted binary file: {len(content_data)} bytes")
            except:
                text_content = f"[Binary file: {layer['filename']}]"
                print(f"[MULTI-LAYER] Extracted binary file (decode failed): {len(content_data)} bytes")
            
            return {
                'success': True,
                'single_extraction': True,
                'extracted_data': text_content,
                'filename': layer['filename'],
                'layer_number': layer['layer_number'],
                'total_layers_found': len(existing_layers),
                'saved_to': layer.get('saved_to'),
                'binary_content': content_data  # CRITICAL: Include the actual binary data
            }
        
        # Multiple layers - create zip file
        return self._create_multi_layer_response(extracted_layers, output_dir, len(layers))
    
    def _extract_single_layer(self, file_data: bytes, layer_info: Dict, password: Optional[str]) -> Optional[Dict[str, Any]]:
        """Extract a single layer from file data"""
        
        magic_header = layer_info['magic_header']
        end_marker = layer_info['end_marker']
        magic_pos = layer_info['magic_pos']
        
        try:
            # Handle legacy format
            if magic_header == self.legacy_magic:
                return self._extract_legacy_layer(file_data, magic_pos, password)
            
            # Parse metadata
            metadata_size_pos = magic_pos + len(magic_header)
            metadata_size = int.from_bytes(file_data[metadata_size_pos:metadata_size_pos+4], 'little')
            
            metadata_pos = metadata_size_pos + 4
            metadata_json = file_data[metadata_pos:metadata_pos+metadata_size]
            metadata = json.loads(metadata_json.decode('utf-8'))
            
            # Check password compatibility
            if password:
                provided_hash = hashlib.sha256(password.encode()).hexdigest()
                if metadata.get('password_hash') and metadata['password_hash'] != provided_hash:
                    return None  # Password doesn't match this layer
            elif metadata.get('encrypted', False):
                return None  # Layer is encrypted but no password provided
            
            # Parse data
            data_size_pos = metadata_pos + metadata_size
            data_size = int.from_bytes(file_data[data_size_pos:data_size_pos+4], 'little')
            
            payload_pos = data_size_pos + 4
            payload_data = file_data[payload_pos:payload_pos+data_size]
            
            # Decrypt if needed
            if metadata['encrypted'] and password:
                secret_data = self._decrypt_data(payload_data, password)
            else:
                secret_data = payload_data
            
            return {
                'layer_number': metadata.get('layer_number', 0),
                'layer_id': metadata.get('layer_id', 'legacy'),
                'filename': metadata['filename'],
                'content': secret_data,
                'metadata': metadata
            }
            
        except Exception as e:
            print(f"[MULTI-LAYER] Layer extraction error: {e}")
            return None
    
    def _extract_legacy_layer(self, file_data: bytes, magic_pos: int, password: Optional[str]) -> Optional[Dict[str, Any]]:
        """Extract legacy single-layer format"""
        
        try:
            # Parse metadata (legacy format)
            metadata_size_pos = magic_pos + len(self.legacy_magic)
            metadata_size = int.from_bytes(file_data[metadata_size_pos:metadata_size_pos+4], 'little')
            
            metadata_pos = metadata_size_pos + 4
            metadata_json = file_data[metadata_pos:metadata_pos+metadata_size]
            metadata = json.loads(metadata_json.decode('utf-8'))
            
            # Check encryption compatibility
            if metadata.get('encrypted', False) and not password:
                return None
            elif not metadata.get('encrypted', False) and password:
                return None  # Not encrypted but password provided
            
            # Parse data
            data_size_pos = metadata_pos + metadata_size
            data_size = int.from_bytes(file_data[data_size_pos:data_size_pos+4], 'little')
            
            payload_pos = data_size_pos + 4
            payload_data = file_data[payload_pos:payload_pos+data_size]
            
            # Decrypt if needed
            if metadata['encrypted'] and password:
                secret_data = self._decrypt_data(payload_data, password)
            else:
                secret_data = payload_data
            
            return {
                'layer_number': 0,  # Legacy
                'layer_id': 'legacy',
                'filename': metadata['filename'],
                'content': secret_data,
                'metadata': metadata
            }
            
        except Exception as e:
            print(f"[MULTI-LAYER] Legacy extraction error: {e}")
            return None
    
    def _create_multi_layer_response(self, extracted_layers: List[Dict], output_dir: str, total_layers: int) -> Dict[str, Any]:
        """Create response for multiple extracted layers"""
        
        if not output_dir:
            output_dir = tempfile.mkdtemp()
        
        # Create zip file with all extracted layers
        zip_filename = f"multilayer_extraction_{hashlib.md5(str(len(extracted_layers)).encode()).hexdigest()[:8]}.zip"
        zip_path = os.path.join(output_dir, zip_filename)
        
        layer_info = []
        display_messages = []
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for i, layer in enumerate(extracted_layers):
                # Save individual layer file
                layer_filename = f"layer_{layer['layer_number']}_{layer['filename']}"
                layer_path = os.path.join(output_dir, layer_filename)
                
                with open(layer_path, 'wb') as f:
                    f.write(layer['content'])
                
                # Add to zip
                zipf.write(layer_path, layer_filename)
                
                # Collect info for response
                try:
                    if layer['filename'].endswith(('.txt', '.json', '.py', '.js', '.html', '.css')):
                        text_content = layer['content'].decode('utf-8')
                        display_messages.append(f"Layer {layer['layer_number']}: {text_content[:200]}...")
                    else:
                        display_messages.append(f"Layer {layer['layer_number']}: [Binary file: {layer['filename']}]")
                except:
                    display_messages.append(f"Layer {layer['layer_number']}: [Binary file: {layer['filename']}]")
                
                layer_info.append({
                    'layer_number': layer['layer_number'],
                    'filename': layer['filename'],
                    'size': len(layer['content']),
                    'saved_as': layer_filename
                })
                
                # Clean up individual file
                os.remove(layer_path)
        
        return {
            'success': True,
            'multi_layer_extraction': True,
            'total_layers_extracted': len(extracted_layers),
            'total_layers_found': total_layers,
            'zip_file': zip_path,
            'zip_filename': zip_filename,
            'extracted_data': '\n\n'.join(display_messages),
            'layer_details': layer_info
        }
    
    def _encrypt_data(self, data: bytes, password: str) -> bytes:
        """Encrypt data using AES-GCM"""
        salt = os.urandom(16)
        nonce = os.urandom(12)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(password.encode())
        
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        
        return salt + nonce + ciphertext
    
    def _decrypt_data(self, encrypted_data: bytes, password: str) -> bytes:
        """Decrypt data using AES-GCM"""
        salt = encrypted_data[:16]
        nonce = encrypted_data[16:28]
        ciphertext = encrypted_data[28:]
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(password.encode())
        
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None)

# Backward compatibility wrapper
class UniversalFileSteganography(FixedMultiLayerSteganography):
    """Backward compatible wrapper using fixed multilayer implementation"""
    
    def __init__(self):
        super().__init__()
    
    def extract_data(self, stego_file_path: str, password: Optional[str] = None, 
                     output_dir: str = None) -> Optional[Union[Tuple[bytes, str], Dict[str, Any]]]:
        """
        FIXED: Use corrected multi-layer extraction
        """
        
        try:
            print(f"[FIXED-MULTILAYER EXTRACT] Using fixed extraction method")
            result = self.extract_all_layers(stego_file_path, password, output_dir)
            
            if not result or not result.get('success'):
                return None
            
            if output_dir:
                return result
            else:
                # Handle single extraction case
                if result.get('single_extraction'):
                    filename = result.get('filename', 'extracted_data.txt')
                    text_data = result.get('extracted_data', '')
                    
                    if isinstance(text_data, str):
                        return (text_data.encode('utf-8'), filename)
                    else:
                        return (text_data, filename)
                else:
                    # Multiple layers
                    layers = result.get('extracted_layers', [])
                    if layers:
                        first_layer = layers[0]
                        filename = first_layer.get('filename', 'extracted_data.txt')
                        content = first_layer.get('content', b'')
                        return (content, filename)
                return None
        
        except Exception as e:
            print(f"Fixed extraction error: {e}")
            return None
    
    def _try_legacy_extraction(self, file_data: bytes, password: Optional[str]) -> Optional[Dict[str, Any]]:
        """Try to extract data using legacy format for backward compatibility"""
        try:
            # Look for legacy magic header
            legacy_pos = file_data.find(self.legacy_magic)
            if legacy_pos == -1:
                return None
            
            print("[FIXED-MULTILAYER] Found legacy format, attempting extraction...")
            
            # Parse legacy metadata
            metadata_size_pos = legacy_pos + len(self.legacy_magic)
            metadata_size = int.from_bytes(file_data[metadata_size_pos:metadata_size_pos+4], 'little')
            
            metadata_pos = metadata_size_pos + 4
            metadata_json = file_data[metadata_pos:metadata_pos+metadata_size]
            metadata = json.loads(metadata_json.decode('utf-8'))
            
            # Check encryption compatibility
            if metadata.get('encrypted', False) and not password:
                return None
            elif not metadata.get('encrypted', False) and password:
                return None
            
            # Parse data
            data_size_pos = metadata_pos + metadata_size
            data_size = int.from_bytes(file_data[data_size_pos:data_size_pos+4], 'little')
            
            payload_pos = data_size_pos + 4
            payload_data = file_data[payload_pos:payload_pos+data_size]
            
            # Decrypt if needed
            if metadata['encrypted'] and password:
                secret_data = self._decrypt_data(payload_data, password)
            else:
                secret_data = payload_data
            
            return {
                'success': True,
                'single_extraction': True,
                'extracted_data': secret_data.decode('utf-8', errors='replace'),
                'filename': metadata.get('filename', 'legacy_extracted.txt'),
                'layer_number': 0,
                'total_layers_found': 1,
                'binary_content': secret_data
            }
            
        except Exception as e:
            print(f"[FIXED-MULTILAYER] Legacy extraction failed: {e}")
            return None

# Legacy compatibility function
def extract_layered_data_container(layered_container_json: bytes) -> List[Tuple[bytes, str]]:
    """
    Extract layers from a layered container JSON - for backward compatibility
    """
    try:
        # Use the fixed multilayer class to handle this
        container_str = layered_container_json.decode('utf-8')
        container = json.loads(container_str)
        
        if container.get('type') == 'fixed_multilayer_container':
            # New format
            layers = container.get('layers', [])
            extracted_layers = []
            
            for layer in layers:
                layer_filename = layer.get('filename', f'layer_{layer.get("layer_number", 0)}.bin')
                layer_content = layer.get('content_base64', '')
                
                try:
                    layer_data = base64.b64decode(layer_content)
                    extracted_layers.append((layer_data, layer_filename))
                    print(f"[FIXED-MULTILAYER] Extracted layer: {layer_filename} ({len(layer_data)} bytes)")
                except Exception as e:
                    print(f"[FIXED-MULTILAYER] Failed to decode layer {layer_filename}: {e}")
            
            return extracted_layers
        
        # Old format - handle for backward compatibility
        elif container.get('type') == 'layered_container':
            layers = container.get('layers', [])
            extracted_layers = []
            
            for layer in layers:
                layer_filename = layer.get('filename', f'layer_{layer.get("index", 0)}.bin')
                layer_type = layer.get('type', 'binary')
                layer_content = layer.get('content', '')
                
                if layer_type == 'binary':
                    try:
                        layer_data = base64.b64decode(layer_content)
                    except Exception as e:
                        print(f"[LEGACY] Failed to decode base64 for {layer_filename}: {e}")
                        continue
                elif layer_type == 'text':
                    try:
                        decoded_bytes = base64.b64decode(layer_content)
                        layer_data = decoded_bytes
                    except Exception as e:
                        print(f"[LEGACY] Failed to decode base64 text for {layer_filename}: {e}")
                        layer_data = layer_content.encode('utf-8')
                else:
                    layer_data = layer_content.encode('utf-8')
                
                extracted_layers.append((layer_data, layer_filename))
                print(f"[LEGACY] Extracted layer: {layer_filename} ({len(layer_data)} bytes)")
            
            return extracted_layers
        
        return []
        
    except Exception as e:
        print(f"[EXTRACT ERROR] Failed to extract container: {e}")
        return []