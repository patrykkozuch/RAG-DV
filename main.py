import torch

from src.frontend.app import main as App

torch.classes.__path__ = []  # Neutralizes the path inspection


if __name__ == "__main__":
    App()