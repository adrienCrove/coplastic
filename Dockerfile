FROM odoo:17.0

USER root

# Dépendances Python supplémentaires si nécessaire
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt || true

# Copie des modules custom
COPY ./custom_addons /mnt/extra-addons

# Configuration
COPY ./odoo.conf /etc/odoo/odoo.conf

USER odoo