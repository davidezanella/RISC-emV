from riscemv.ReservationStations import ReservationStations
from riscemv.RegisterFile import RegisterFile
from riscemv.RegisterStatus import RegisterStatus
from riscemv.ProgramLoader import ProgramLoader
from riscemv.InstructionBuffer import InstructionBuffer
from riscemv.DataMemory import DataMemory
from riscemv.ISA.RType_Instruction import RType_Instruction
from riscemv.ISA.IType_Instruction import IType_Instruction
from riscemv.ISA.SType_Instruction import SType_Instruction
import queue

class Tomasulo:
    def __init__(self, XLEN, adders_number, multipliers_number, dividers_number, loaders_number, storers_number):
        self.__steps = 0

        self.IFQ = InstructionBuffer()
        self.Regs = RegisterFile()
        self.RegisterStat = RegisterStatus()
        self.RS = ReservationStations(adders_number, multipliers_number, dividers_number, loaders_number, storers_number)
        self.DM = DataMemory()


    def step(self):
        self.__steps += 1
        print("[TOM] Performing step number", self.__steps)

        self.write()
        self.execute()
        self.issue()


    def issue(self):
        if self.IFQ.empty():
            print("[TOM] IFQ is empty")
        else:
            ifq_entry = self.IFQ.get()
            instruction = ifq_entry.instruction
            print("[TOM] Issuing", instruction)
            fu = self.RS.get_first_free(instruction.functional_unit)

            if fu is None:
                # TODO: instruction gets lost
                print("All RS busy, stalling")
            else:
                fu.instruction = instruction
                fu.time_remaining = instruction.clock_needed

                if isinstance(instruction, RType_Instruction):
                    if self.RegisterStat.get_int_status(instruction.rs1) is not None:
                        fu.Qj = self.RegisterStat.get_int_status(instruction.rs1)
                    else:
                        fu.Vj = self.Regs.readInt(instruction.rs1)
                        fu.Qj = 0
                    if self.RegisterStat.get_int_status(instruction.rs2) is not None:
                        fu.Qk = self.RegisterStat.get_int_status(instruction.rs2)
                    else:
                        fu.Vk = self.Regs.readInt(instruction.rs2)
                        fu.Qk = 0
                elif isinstance(instruction, IType_Instruction):
                    if self.RegisterStat.get_int_status(instruction.rs) is not None:
                        fu.Qj = self.RegisterStat.get_int_status(instruction.rs)
                    else:
                        fu.Vj = self.Regs.readInt(instruction.rs)
                        fu.Qj = 0
                    fu.A = instruction.imm # store the immediate value
                    fu.Qk = 0
                elif isinstance(instruction, SType_Instruction):
                    if self.RegisterStat.get_int_status(instruction.rs1) is not None:
                        fu.Qj = self.RegisterStat.get_int_status(instruction.rs1)
                    else:
                        fu.Vj = self.Regs.readInt(instruction.rs1)
                        fu.Qj = 0
                    fu.A = instruction.imm # store the immediate value
                    fu.Qk = 0
                    if self.RegisterStat.get_int_status(instruction.rs2) is not None:
                        fu.Qk = self.RegisterStat.get_int_status(instruction.rs2)
                    else:
                        fu.Vk = self.Regs.readInt(instruction.rs2)
                        fu.Qk = 0

                print(fu.Vj, fu.Vk, fu.Qj, fu.Qk)
                if not isinstance(instruction, SType_Instruction):
                    self.RegisterStat.add_int_status(instruction.rd, fu.name)


    def execute(self):
        for fu in self.RS:
            if fu.busy and fu.time_remaining > 0 and fu.Qj == 0 and fu.Qk == 0:
                fu.time_remaining -= 1
                print("[TOM.EX]", fu.name, fu.time_remaining)

                if fu.time_remaining == 0:
                    if isinstance(fu.instruction, RType_Instruction):
                        fu.result = fu.instruction.execute(fu.Vj, fu.Vk)
                    elif isinstance(fu.instruction, IType_Instruction):
                        if fu.instruction.is_load():
                            fu.A = fu.instruction.execute(fu.Vj) # TODO: split in two cycles
                            fu.result = self.DM.load(fu.A)
                        else:
                            fu.result = fu.instruction.execute(fu.Vj)
                    elif isinstance(fu.instruction, SType_Instruction):
                        fu.A = fu.instruction.execute(fu.Vj)


    def write(self):
        for fu in self.RS:
            if fu.busy and fu.time_remaining == 0:
                if isinstance(fu.instruction, SType_Instruction):
                    self.DM.store(fu.A, fu.Vk)
                else:
                    self.RegisterStat.remove_int_status(fu.instruction.rd)
                    self.Regs.writeInt(fu.instruction.rd, fu.result)

                    # Write result
                    for other_fu in self.RS:
                        if other_fu.Qj == fu.name:
                            other_fu.Vj = fu.result
                            other_fu.Qj = 0
                        elif other_fu.Qk == fu.name:
                            other_fu.Vk = fu.result
                            other_fu.Qk = 0

                fu.clear()
