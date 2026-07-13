from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_vllm_start_script_uses_docker_image_and_local_model_mount():
    script = (ROOT / "scripts" / "start_vllm_tp8_qwen32b.sh").read_text(encoding="utf-8")

    assert "vllm/vllm-openai:latest" in script
    assert "/home/user/models/Qwen2.5-Coder-32B-Instruct" in script
    assert "--gpus all" in script
    assert "--ipc=host" in script
    assert "-v \"${HOST_MODEL_PATH}:${CONTAINER_MODEL_PATH}:ro\"" in script
    assert "--tensor-parallel-size 8" in script
    assert "--model \"${CONTAINER_MODEL_PATH}\"" in script
