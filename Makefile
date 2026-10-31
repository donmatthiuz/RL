# Tareas de apoyo del proyecto.

# Claves locales en keys/<nombre>.key. Para un servicio nuevo, agregar su nombre aquí.
KEYS := context7

.PHONY: keys-init
keys-init: ## Crea los archivos de claves vacíos en keys/ sin sobrescribir los existentes
	@mkdir -p keys
	@for k in $(KEYS); do \
		f="keys/$$k.key"; \
		if [ -e "$$f" ]; then \
			echo "$$f ya existe, no se modifica"; \
		else \
			: > "$$f"; chmod 600 "$$f"; \
			echo "$$f creado: pega la clave en una sola línea"; \
		fi; \
	done
