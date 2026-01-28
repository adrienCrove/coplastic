FROM odoo:17.0

USER root

# Dépendances Python supplémentaires
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt || true
# Installer openai séparément (requis pour cosplastic_bot)
RUN pip3 install --no-cache-dir openai

# Copie des modules custom
COPY ./custom_addons /mnt/extra-addons

# Configuration
COPY ./odoo.conf /etc/odoo/odoo.conf

USER odoo