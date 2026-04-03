PROJECT := wyoming-faster-qwen3-tts

.PHONY: clean clean-app clean-runtime clean-docker rebuild-docker

clean: clean-app clean-runtime

clean-app:
	find . -type d \( -name '__pycache__' -o -name '.pytest_cache' -o -name 'build' -o -name 'dist' -o -name '*.egg-info' \) -prune -exec rm -rf {} +

clean-runtime:
	find . \( -path './outputs/*' -o -path './output/*' -o -path './tmp/*' -o -path './temp/*' -o -path './data/outputs/*' -o -path './data/tmp/*' \) \
		\( -name '*.wav' -o -name '*.mp3' -o -name '*.flac' -o -name '*.ogg' -o -name '*.tmp' -o -name '*.part' -o -name '*.partial' -o -name '*.download' -o -name '*.incomplete' \) \
		-delete

clean-docker:
	docker compose down --remove-orphans --volumes || true
	docker rm -f $(PROJECT) 2>/dev/null || true
	docker image rm -f $(PROJECT):latest 2>/dev/null || true
	docker builder prune -af
	docker image prune -f
	docker container prune -f
	docker volume prune -f

rebuild-docker: clean-docker
	docker compose build --no-cache
	docker compose up -d
