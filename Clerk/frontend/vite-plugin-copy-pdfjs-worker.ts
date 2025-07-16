import { Plugin } from 'vite';
import fs from 'fs';
import path from 'path';

/**
 * Vite plugin to copy PDF.js worker file to public directory.
 * This ensures the worker is available at the expected path.
 */
export function copyPdfJsWorker(): Plugin {
  return {
    name: 'copy-pdfjs-worker',
    buildStart() {
      const workerSrc = path.resolve(
        __dirname,
        'node_modules/pdfjs-dist/build/pdf.worker.min.js'
      );
      const workerDest = path.resolve(__dirname, 'public/pdf.worker.min.js');

      try {
        // Check if source file exists
        if (fs.existsSync(workerSrc)) {
          // Create public directory if it doesn't exist
          const publicDir = path.dirname(workerDest);
          if (!fs.existsSync(publicDir)) {
            fs.mkdirSync(publicDir, { recursive: true });
          }

          // Copy the worker file
          fs.copyFileSync(workerSrc, workerDest);
          console.log('✓ PDF.js worker copied to public directory');
        } else {
          console.warn('⚠️  PDF.js worker not found at:', workerSrc);
        }
      } catch (error) {
        console.error('Error copying PDF.js worker:', error);
      }
    },
  };
}