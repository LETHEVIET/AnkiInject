import sharp from 'sharp';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Paths
const PROJECT_ROOT = path.resolve(__dirname, '../../');
const PACKAGING_DIR = path.join(PROJECT_ROOT, 'packaging');
const PUBLIC_DIR = path.join(PROJECT_ROOT, 'frontend/public');

// Ensure output dirs exist
if (!fs.existsSync(PACKAGING_DIR)) fs.mkdirSync(PACKAGING_DIR, { recursive: true });
if (!fs.existsSync(PUBLIC_DIR)) fs.mkdirSync(PUBLIC_DIR, { recursive: true });

async function generateIcon(size, outputPath) {
  const canvasSize = 512;
  // Scaled dimensions for the card
  // Card Geometry - Rectangle (3:2 approx ratio)
  const cx = canvasSize / 2;
  const cy = canvasSize / 2;
  const cardW = 440; 
  const cardH = 300;
  const cardR = 40;

  // Colors
  const colors = {
    cardBg: '#ffffff',
    cardBorder: '#e2e8f0',
    stackBorder: '#cbd5e1',
    ankiText: '#0f172a', 
    injectText: '#2563eb', 
    shadow: 'rgba(15, 23, 42, 0.12)'
  };

  // SVG Composition
  const svgComposite = `
  <svg width="${canvasSize}" height="${canvasSize}" viewBox="0 0 ${canvasSize} ${canvasSize}" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="cardGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" style="stop-color: #ffffff; stop-opacity: 1" />
        <stop offset="100%" style="stop-color: #f8fafc; stop-opacity: 1" />
      </linearGradient>

      <filter id="cleanShadow" x="-20%" y="-20%" width="140%" height="160%">
        <feGaussianBlur in="SourceAlpha" stdDeviation="8" />
        <feOffset dx="0" dy="10" result="offsetblur" />
        <feFlood flood-color="#000" flood-opacity="0.1" />
        <feComposite in2="offsetblur" operator="in" />
        <feMerge>
          <feMergeNode />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>

      <pattern id="dotPattern" width="20" height="20" patternUnits="userSpaceOnUse">
        <circle cx="2" cy="2" r="1" fill="#cbd5e1" opacity="0.4" />
      </pattern>
    </defs>

    <!-- Stack Layer 3 -->
    <rect 
      x="${cx - cardW / 2 + 20}" y="${cy - cardH / 2 - 30}" 
      width="${cardW}" height="${cardH}" 
      rx="${cardR}" 
      fill="#f1f5f9" 
      stroke="${colors.stackBorder}"
      stroke-width="1"
      transform="rotate(-4, ${cx}, ${cy})"
    />

    <!-- Stack Layer 2 -->
    <rect 
      x="${cx - cardW / 2 + 10}" y="${cy - cardH / 2 - 15}" 
      width="${cardW}" height="${cardH}" 
      rx="${cardR}" 
      fill="#f8fafc" 
      stroke="${colors.stackBorder}"
      stroke-width="1"
      transform="rotate(-2, ${cx}, ${cy})"
    />

    <!-- Main Card -->
    <rect 
      x="${cx - cardW / 2}" y="${cy - cardH / 2}" 
      width="${cardW}" height="${cardH}" 
      rx="${cardR}" 
      fill="url(#cardGrad)" 
      filter="url(#cleanShadow)"
      stroke="${colors.cardBorder}"
      stroke-width="1.5"
    />

    <!-- Subtle Texture -->
    <rect 
      x="${cx - cardW / 2}" y="${cy - cardH / 2}" 
      width="${cardW}" height="${cardH}" 
      rx="${cardR}" 
      fill="url(#dotPattern)" 
    />

    <!-- AI Sparkle Icon - Scaled up to 0.85 for more visual impact -->
    <g transform="translate(${cx - 195}, ${cy - 128}) scale(0.85)">
      <path 
        d="M32 0C32 17.6731 46.3269 32 64 32C46.3269 32 32 46.3269 32 64C32 46.3269 17.6731 32 0 32C17.6731 32 32 17.6731 32 0Z" 
        fill="${colors.injectText}" 
      />
      <path 
        d="M60 45C60 51.6274 65.3726 57 72 57C65.3726 57 60 62.3726 60 69C60 62.3726 54.6274 57 48 57C54.6274 57 60 51.6274 60 45Z" 
        fill="${colors.injectText}"
        opacity="0.5"
      />
    </g>

    <!-- Centered Typography -->
    <g transform="translate(${cx}, ${cy})" text-anchor="middle" font-weight="900" letter-spacing="-2" font-family="Inter, system-ui, sans-serif">
        <text x="0" y="-10" font-size="95" fill="${colors.ankiText}">
          Anki
        </text>
        
        <text x="0" y="90" font-size="95" fill="${colors.injectText}">
          Inject
        </text>
    </g>
  </svg>
  `;

  // Generate PNG using Sharp
  await sharp(Buffer.from(svgComposite))
    .resize(size, size) // High quality resize
    .png()
    .toFile(outputPath);
  
  console.log(`Generated Stacked Text Icon: ${outputPath} (${size}x${size})`);
}

async function main() {
  console.log('✨ Generating Stacked Text Icons...');
  
  const sizes = [16, 32, 48, 64, 128, 256, 512];
  
  // Packaging Icons
  for (const s of sizes) {
    await generateIcon(s, path.join(PACKAGING_DIR, `icon_${s}.png`));
  }
  
  // Main App Icon
  await generateIcon(512, path.join(PACKAGING_DIR, 'anki-inject.png'));
  
  // Frontend Assets
  await generateIcon(512, path.join(PUBLIC_DIR, 'logo.png'));
  await generateIcon(64, path.join(PUBLIC_DIR, 'favicon.png'));
}

main().catch(console.error);
