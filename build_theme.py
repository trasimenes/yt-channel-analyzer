#!/usr/bin/env python3
"""
Script pour compiler les thèmes SCSS Sneat avec Dart Sass
"""

import os
import subprocess
import sys

def compile_scss():
    """Compile les fichiers SCSS en CSS"""
    print("🎨 Compilation des thèmes SCSS...")
    
    # Définir les chemins
    scss_dir = "static/sneat/scss"
    css_output_dir = "static/sneat/assets/vendor/css"
    
    # Vérifier que le dossier SCSS existe
    if not os.path.exists(scss_dir):
        print(f"❌ Dossier SCSS non trouvé: {scss_dir}")
        return False
    
    # Créer le dossier de sortie
    os.makedirs(css_output_dir, exist_ok=True)
    
    # Fichiers à compiler
    files_to_compile = [
        {
            "input": f"{scss_dir}/core-simple.scss",
            "output": f"{css_output_dir}/core.css"
        },
        {
            "input": f"{scss_dir}/theme-default-simple.scss", 
            "output": f"{css_output_dir}/theme-default.css"
        }
    ]
    
    # Vérifier si dart-sass est disponible
    sass_cmd = None
    for cmd in ['sass', 'dart-sass/sass', './dart-sass/sass']:
        try:
            subprocess.run([cmd, '--version'], capture_output=True, check=True)
            sass_cmd = cmd
            print(f"✅ Dart Sass trouvé: {cmd}")
            break
        except:
            continue
    
    if not sass_cmd:
        print("❌ Dart Sass non trouvé. Installation requise.")
        return False
    
    # Compiler chaque fichier
    success_count = 0
    for file_config in files_to_compile:
        input_file = file_config["input"]
        output_file = file_config["output"]
        
        if not os.path.exists(input_file):
            print(f"⚠️ Fichier source manquant: {input_file}")
            continue
        
        try:
            print(f"📝 Compilation: {os.path.basename(input_file)}")
            result = subprocess.run([
                sass_cmd,
                "--style=compressed",
                input_file,
                output_file
            ], capture_output=True, text=True, check=True)
            
            # Vérifier la taille du fichier généré
            if os.path.exists(output_file):
                size = os.path.getsize(output_file)
                print(f"✅ {os.path.basename(output_file)} généré ({size} bytes)")
                success_count += 1
            else:
                print(f"❌ Échec de la génération: {output_file}")
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Erreur de compilation pour {input_file}:")
            print(f"   {e.stderr}")
    
    print(f"\n✨ Compilation terminée: {success_count}/{len(files_to_compile)} fichiers")
    return success_count > 0

if __name__ == "__main__":
    success = compile_scss()
    sys.exit(0 if success else 1)