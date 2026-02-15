# Makefile for fedorajam-audio-config translations
#
# Usage:
#   make          - compile all .po files to .mo
#   make update   - regenerate the .pot template from source
#   make install  - install .mo files to DESTDIR/usr/share/locale
#   make clean    - remove compiled .mo files
#
DOMAIN   = fedorajam-audio-config
SRCDIR   = ../usr/share/fedorajam-audio-config
POTFILE  = $(DOMAIN).pot
DESTDIR ?=
PREFIX  ?= /usr/share/locale

POFILES  = $(wildcard *.po)
MOFILES  = $(POFILES:.po=.mo)
LANGS    = $(basename $(POFILES))

.PHONY: all update install clean

all: $(MOFILES)

%.mo: %.po
	msgfmt --check --statistics -o $@ $<

update: $(POTFILE)

$(POTFILE):
	xgettext --language=Python --keyword=_ \
		--package-name=$(DOMAIN) \
		--package-version=1.0 \
		--msgid-bugs-address=erich@ericheickmeyer.com \
		--output=$@ \
		$(SRCDIR)/i18n.py \
		$(SRCDIR)/backend/audio_config.py \
		$(SRCDIR)/ui/base.py \
		$(SRCDIR)/ui/gtk_ui.py \
		$(SRCDIR)/ui/qt_ui.py \
		$(SRCDIR)/main.py

install: $(MOFILES)
	@for lang in $(LANGS); do \
		dir=$(DESTDIR)$(PREFIX)/$$lang/LC_MESSAGES; \
		echo "Installing $$lang → $$dir/$(DOMAIN).mo"; \
		install -d $$dir; \
		install -m 644 $$lang.mo $$dir/$(DOMAIN).mo; \
	done

clean:
	rm -f $(MOFILES)
