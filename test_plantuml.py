"""
Test script to verify PlantUML server connectivity and WBS rendering
"""
import zlib
import base64
import urllib.request

def test_plantuml_render():
    """Test PlantUML rendering with a simple WBS diagram"""
    
    # Simple WBS test code
    test_wbs = """@startwbs
* Project
** Phase 1
*** Task 1
*** Task 2
** Phase 2
*** Task 3
@endwbs"""
    
    print("Testing PlantUML rendering...")
    print(f"Source code:\n{test_wbs}\n")
    
    # PlantUML encoding
    plantuml_alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'
    
    def encode3bytes(b1, b2, b3):
        c1 = b1 >> 2
        c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
        c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
        c4 = b3 & 0x3F
        return (plantuml_alphabet[c1 & 0x3F] +
                plantuml_alphabet[c2 & 0x3F] +
                plantuml_alphabet[c3 & 0x3F] +
                plantuml_alphabet[c4 & 0x3F])
    
    # Compress and encode
    compressed = zlib.compress(test_wbs.encode('utf-8'))[2:-4]
    result = []
    for i in range(0, len(compressed), 3):
        if i + 2 < len(compressed):
            result.append(encode3bytes(compressed[i], compressed[i + 1], compressed[i + 2]))
        elif i + 1 < len(compressed):
            result.append(encode3bytes(compressed[i], compressed[i + 1], 0))
        else:
            result.append(encode3bytes(compressed[i], 0, 0))
    
    encoded = ''.join(result)
    
    # Test with PlantUML server
    plantuml_url = "https://www.plantuml.com/plantuml"
    url = f"{plantuml_url}/svg/{encoded}"
    
    print(f"PlantUML URL: {url}\n")
    
    try:
        response = urllib.request.urlopen(url, timeout=30)
        content = response.read()
        content_type = response.headers.get('content-type')
        
        print(f"Status code: {response.status}")
        print(f"Content type: {content_type}")
        print(f"Content length: {len(content)} bytes")
        
        if response.status == 200:
            # Save SVG to file
            with open("test_wbs_output.svg", "wb") as f:
                f.write(content)
            print("\n✅ SUCCESS! SVG saved to test_wbs_output.svg")
            
            # Create data URL
            encoded_svg = base64.b64encode(content).decode('utf-8')
            data_url = f"data:image/svg+xml;base64,{encoded_svg}"
            print(f"\nData URL length: {len(data_url)} characters")
            print(f"Data URL preview: {data_url[:100]}...")
            
            # Show first 500 chars of SVG
            print(f"\nSVG content preview:\n{content.decode('utf-8')[:500]}...")
        else:
            print(f"\n❌ ERROR: Status {response.status}")
                
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")

if __name__ == "__main__":
    test_plantuml_render()
