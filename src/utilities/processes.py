import psutil
import os

class Processes:

    @staticmethod
    def are_processes_running(required_processes=["VALORANT-Win64-Shipping.exe", "RiotClientServices.exe"]):
        processes = []
        for proc in psutil.process_iter():
            try:
                processes.append(proc.name())
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # le processus a disparu ou n'est pas accessible, on l'ignore
                continue
        
        return set(required_processes).issubset(processes)

    @staticmethod
    def is_program_already_running():
        processes = []
        for proc in psutil.process_iter():
            try:
                processes.append(proc.name())
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if len([proc for proc in processes if proc == "valorant-rpc.exe"]) > 2:
            return True

        return False