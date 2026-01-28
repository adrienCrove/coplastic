#!/usr/bin/env python3
"""
Script pour télécharger la documentation technique/développeur Odoo 17
et la convertir en fichiers texte pour le RAG
"""

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import re

BASE_URL = "https://www.odoo.com/documentation/17.0/developer/"
OUTPUT_DIR = "/root/co-plastic/odoo17/docs/odoo17_tech_docs"

# Sections techniques/développeur à télécharger
SECTIONS = [
    # Tutorials
    "tutorials/define_module_data.html",
    "tutorials/restrict_data_access.html",
    "tutorials/unit_tests.html",
    "tutorials/pdf_reports.html",
    "tutorials/master_odoo_web_framework.html",

    # Reference - Backend
    "reference/backend/orm.html",
    "reference/backend/data.html",
    "reference/backend/actions.html",
    "reference/backend/views.html",
    "reference/backend/reports.html",
    "reference/backend/security.html",
    "reference/backend/module.html",
    "reference/backend/http.html",
    "reference/backend/mixins.html",
    "reference/backend/cmdline.html",

    # Reference - Frontend
    "reference/frontend/javascript_reference.html",
    "reference/frontend/owl_components.html",
    "reference/frontend/registries.html",
    "reference/frontend/services.html",
    "reference/frontend/hooks.html",
    "reference/frontend/patching_code.html",
    "reference/frontend/assets.html",
    "reference/frontend/qweb.html",

    # Reference - Standard Modules
    "reference/standard_modules/mail.html",
    "reference/standard_modules/payment.html",
    "reference/standard_modules/website.html",

    # How-to guides
    "howtos/create_reports.html",
    "howtos/javascript.html",
    "howtos/scss_tips.html",

    # Upgrade
    "reference/upgrades/upgrade_scripts.html",
]

def clean_text(text):
    """Nettoie le texte extrait"""
    # Supprimer les espaces multiples
    text = re.sub(r'\s+', ' ', text)
    # Supprimer les lignes vides multiples
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

def extract_code_blocks(soup):
    """Extrait et préserve les blocs de code"""
    code_blocks = []
    for code in soup.find_all(['pre', 'code']):
        code_text = code.get_text()
        if len(code_text) > 10:  # Ignorer les petits snippets inline
            code_blocks.append(code_text)
    return code_blocks

def extract_content(soup):
    """Extrait le contenu principal de la page"""
    # Trouver le contenu principal
    main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='document')

    if not main_content:
        main_content = soup.find('body')

    if main_content:
        # Supprimer les éléments de navigation
        for nav in main_content.find_all(['nav', 'aside', 'header', 'footer']):
            nav.decompose()

        # Préserver les blocs de code
        code_blocks = extract_code_blocks(main_content)

        # Extraire le texte
        text = main_content.get_text(separator='\n')
        text = clean_text(text)

        # Ajouter les blocs de code importants à la fin
        if code_blocks:
            text += "\n\n--- EXEMPLES DE CODE ---\n\n"
            for i, code in enumerate(code_blocks[:10], 1):  # Max 10 blocs de code
                text += f"\nExemple {i}:\n```\n{code}\n```\n"

        return text

    return ""

def download_page(url, output_file):
    """Télécharge une page et extrait le contenu"""
    try:
        print(f"Téléchargement: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; OdooDocBot/1.0)'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extraire le titre
        title = soup.find('h1')
        title_text = title.get_text() if title else "Sans titre"

        # Extraire le contenu
        content = extract_content(soup)

        if len(content) < 100:
            print(f"  ⚠ Contenu trop court, ignoré")
            return False

        # Sauvegarder
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# {title_text}\n\n")
            f.write(f"Source: {url}\n")
            f.write(f"Type: Documentation Technique Odoo 17\n\n")
            f.write("---\n\n")
            f.write(content)

        print(f"  ✓ Sauvegardé: {output_file}")
        return True

    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        return False

def get_sub_pages(url):
    """Récupère les sous-pages d'une section"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; OdooDocBot/1.0)'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Trouver les liens vers les sous-pages
        links = []
        toc = soup.find('div', class_='toctree-wrapper') or soup.find('nav')

        if toc:
            for a in toc.find_all('a', href=True):
                href = a['href']
                if href.startswith('#') or href.startswith('http'):
                    continue
                full_url = urljoin(url, href)
                if full_url not in links and 'documentation/17.0' in full_url:
                    links.append(full_url)

        return links[:15]  # Limiter à 15 sous-pages par section

    except Exception as e:
        print(f"Erreur récupération sous-pages: {e}")
        return []

def main():
    # Créer le dossier de sortie
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    total_pages = 0
    failed_pages = 0

    for section in SECTIONS:
        section_url = BASE_URL + section

        # Déterminer la catégorie (tutorials, reference, howtos, etc.)
        parts = section.split('/')
        if len(parts) >= 2:
            category = parts[0]
            subcategory = parts[1] if len(parts) > 2 else ""
            page_name = parts[-1].replace('.html', '')
        else:
            category = "general"
            subcategory = ""
            page_name = section.replace('.html', '')

        # Créer le dossier de sortie
        if subcategory:
            section_dir = os.path.join(OUTPUT_DIR, category, subcategory)
        else:
            section_dir = os.path.join(OUTPUT_DIR, category)
        os.makedirs(section_dir, exist_ok=True)

        print(f"\n{'='*50}")
        print(f"Section: {category}/{subcategory}/{page_name}" if subcategory else f"Section: {category}/{page_name}")
        print(f"{'='*50}")

        # Télécharger la page principale
        main_file = os.path.join(section_dir, f"{page_name}.txt")
        if download_page(section_url, main_file):
            total_pages += 1
        else:
            failed_pages += 1

        # Télécharger les sous-pages
        sub_pages = get_sub_pages(section_url)
        for i, sub_url in enumerate(sub_pages):
            sub_name = sub_url.split('/')[-1].replace('.html', '')
            sub_file = os.path.join(section_dir, f"{i+1:02d}_{sub_name}.txt")

            if download_page(sub_url, sub_file):
                total_pages += 1
            else:
                failed_pages += 1

            time.sleep(0.5)  # Pause entre les requêtes

    print(f"\n{'='*50}")
    print(f"Terminé!")
    print(f"  - Pages téléchargées: {total_pages}")
    print(f"  - Échecs: {failed_pages}")
    print(f"  - Dossier: {OUTPUT_DIR}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
