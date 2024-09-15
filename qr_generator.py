import qrcode
from urllib.parse import quote
import io
import base64

def generate_upi_qr(amount):
    currency = "INR"
    f_amount = f"{amount:.2f}"

    pay_url = (
        f"upi://pay?pa=rohanbansode567-1@okicici&pn=Rohan%20Bansode"
        f"&am={quote(f_amount)}&cu={quote(currency)}"
        f"&aid=uGICAgIDtz4DWGA"
    )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )

    qr.add_data(pay_url)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    
    # Convert PIL Image to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    # Encode bytes to base64
    img_base64 = base64.b64encode(img_byte_arr).decode('ascii')

    return img_base64

if __name__ == "__main__":
    # Test the function
    test_amount = 100
    qr_code = generate_upi_qr(test_amount)
    print(f"Generated QR code for ₹{test_amount}")
    print(f"Base64 string length: {len(qr_code)}")