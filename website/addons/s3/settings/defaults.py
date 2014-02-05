MAX_RENDER_SIZE = (1024 ** 2) * 3
ALLOWED_ORIGIN = '*'  # 'https://osf.io/' change for staging etc
CORS_RULE = (
    '<CORSRule><AllowedMethod>PUT</AllowedMethod>'
    '<AllowedOrigin>' + ALLOWED_ORIGIN + '</AllowedOrigin>'
    '<AllowedHeader>*</AllowedHeader>'
    '</CORSRule>'
)
