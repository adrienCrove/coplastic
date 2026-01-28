#!/usr/bin/env python3
"""
Script pour télécharger la documentation fonctionnelle Odoo 17
et la convertir en fichiers texte pour le RAG
"""

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import re

BASE_URL = "https://www.odoo.com/documentation/17.0/fr/applications/"
OUTPUT_DIR = "/root/co-plastic/odoo17/docs/odoo17_docs"

# Sections fonctionnelles à télécharger
SECTIONS = [
    "sales/sales.html",
    "sales/crm.html",
    "inventory_and_mrp/inventory.html",
    "inventory_and_mrp/purchase.html",
    "finance/accounting.html",
    "finance/invoicing.html",
    "hr/employees.html",
    "productivity/discuss.html",
]

def clean_text(text):
    """Nettoie le texte extrait"""
    # Supprimer les espaces multiples
    text = re.sub(r'\s+', ' ', text)
    # Supprimer les lignes vides multiples
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

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

        # Extraire le texte
        text = main_content.get_text(separator='\n')
        return clean_text(text)

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

        # Sauvegarder
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# {title_text}\n\n")
            f.write(f"Source: {url}\n\n")
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

        return links[:20]  # Limiter à 20 sous-pages par section

    except Exception as e:
        print(f"Erreur récupération sous-pages: {e}")
        return []

def main():
    # Créer le dossier de sortie
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    total_pages = 0

    for section in SECTIONS:
        section_url = BASE_URL + section
        section_name = section.split('/')[-1].replace('.html', '')
        section_dir = os.path.join(OUTPUT_DIR, section_name)
        os.makedirs(section_dir, exist_ok=True)

        print(f"\n{'='*50}")
        print(f"Section: {section_name}")
        print(f"{'='*50}")

        # Télécharger la page principale
        main_file = os.path.join(section_dir, "index.txt")
        if download_page(section_url, main_file):
            total_pages += 1

        # Télécharger les sous-pages
        sub_pages = get_sub_pages(section_url)
        for i, sub_url in enumerate(sub_pages):
            sub_name = sub_url.split('/')[-1].replace('.html', '')
            sub_file = os.path.join(section_dir, f"{i+1:02d}_{sub_name}.txt")

            if download_page(sub_url, sub_file):
                total_pages += 1

            time.sleep(0.5)  # Pause entre les requêtes

    print(f"\n{'='*50}")
    print(f"Terminé! {total_pages} pages téléchargées")
    print(f"Dossier: {OUTPUT_DIR}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
