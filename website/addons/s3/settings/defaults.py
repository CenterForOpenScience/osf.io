MAX_RENDER_SIZE = (1024 ** 2) * 3
ALLOWED_ORIGIN = 'http://localhost:5000'  # 'https://osf.io/' change for staging etc
CORS_RULE_UPLOAD = (
    '<CORSRule><AllowedMethod>PUT</AllowedMethod><AllowedOrigin>'
    + ALLOWED_ORIGIN +
    '</AllowedOrigin><AllowedHeader>origin</AllowedHeader><AllowedHeader>'
    'Content-Type</AllowedHeader><AllowedHeader>x-amz-acl</AllowedHeader>'
    '<AllowedHeader>Authorization</AllowedHeader></CORSRule>'
)
CORS_RULE_VIEW = (
    '<CORSRule>'
    '<AllowedMethod>GET</AllowedMethod>'
    '<AllowedOrigin>' + ALLOWED_ORIGIN + '</AllowedOrigin>'
    '<AllowedHeader>Content-Disposition</AllowedHeader>'
    '</CORSRule>'
)
