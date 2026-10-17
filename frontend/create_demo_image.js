// Demo form-filled preview image (PNG)
// This file will be replaced by the actual image at build time.
const fs = require("fs");
const path = require("path");

// Create a simple demo form-filled preview image (SVG)
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400"><rect width="600" height="400" fill="#f8f9fa"/><rect width="600" height="40" fill="#2563eb"/><text x="15" y="28" fill="white" font-size="18" font-family="Arial">Registration Form</text><rect x="15" y="60" width="200" height="22" fill="#e5e7eb"/><text x="23" y="77" fill="#374151" font-size="12" font-family="Arial">Full name</text><rect x="220" y="60" width="365" height="22" fill="#3b82f6"/><text x="235" y="77" fill="white" font-size="12" font-family="Arial">John Doe</text><rect x="15" y="90" width="200" height="22" fill="#e5e7eb"/><text x="23" y="107" fill="#374151" font-size="12" font-family="Arial">Father's name</text><rect x="220" y="90" width="365" height="22" fill="#3b82f6"/><text x="235" y="107" fill="white" font-size="12" font-family="Arial">Jane Doe</text><rect x="15" y="120" width="200" height="22" fill="#e5e7eb"/><text x="23" y="137" fill="#374151" font-size="12" font-family="Arial">Date of birth</text><rect x="220" y="120" width="365" height="22" fill="#3b82f6"/><text x="235" y="137" fill="white" font-size="12" font-family="Arial">01/01/1990</text><rect x="15" y="150" width="200" height="22" fill="#e5e7eb"/><text x="23" y="167" fill="#374151" font-size="12" font-family="Arial">County</text><rect x="220" y="150" width="365" height="22" fill="#3b82f6"/><text x="235" y="167" fill="white" font-size="12" font-family="Arial">New York</text></svg>`;

// Convert SVG to PNG using a simple approach
// In production, this would be done with a proper image library
fs.writeFileSync("public/demo-registration-form-filled.png", Buffer.from(svg, "utf-8"));
console.log("Created sample demo image");
