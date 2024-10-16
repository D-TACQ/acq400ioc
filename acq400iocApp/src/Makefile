TOP=../..

include $(TOP)/configure/CONFIG
#----------------------------------------
#  ADD MACRO DEFINITIONS AFTER THIS LINE
#=============================
# Huge kludge by pgm reaches the parts ..
USR_LDFLAGS += -L $(TOP)/lib/$(T_A)

CXXFLAGS+=-fno-operator-names
#=============================
# Build the IOC application

PROD_IOC = acq400ioc
# acq400ioc.dbd will be created and installed
DBD += acq400ioc.dbd

# acq400ioc.dbd will be made up from these files:
acq400ioc_DBD += base.dbd
acq400ioc_DBD += system.dbd
acq400ioc_DBD += xxAcqHost.dbd

acq400ioc_DBD += sysfs.dbd
acq400ioc_DBD += lxb.dbd
acq400ioc_DBD += acqAi.dbd

# Include dbd files from all support applications:
#acq400ioc_DBD += xxx.dbd
acq400ioc_DBD += asyn.dbd
acq400ioc_DBD += drvAsynIPPort.dbd
acq400ioc_DBD += stream.dbd
acq400ioc_DBD += seqSoftIoc.dbd
#acq400ioc_DBD += sncExample.dbd
acq400ioc_DBD += autoRepeat.dbd
acq400ioc_DBD += aoRangeSet.dbd
acq400ioc_DBD += acq43x_setSampleRate.dbd
acq400ioc_DBD += onSetTransient.dbd
acq400ioc_DBD += mgtStopOnLinkDown.dbd
acq400ioc_DBD += calmon.dbd
acq400ioc_DBD += setMB_ClockMonitor.dbd
acq400ioc_DBD += pvmirror.dbd
acq400ioc_DBD += on_delay.dbd
acq400ioc_DBD += clk_freq_flasher.dbd
acq400ioc_DBD += pg4_flasher.dbd
acq400ioc_DBD += sc32_gain_mux.dbd
acq400ioc_DBD += sc32_autozero.dbd
acq400ioc_DBD += atd_range_set.dbd
acq400ioc_DBD += shot_busy.dbd
acq400ioc_DBD += wr_clk_mon.dbd
acq400ioc_DBD += badledfixer.dbd
acq400ioc_DBD += mgt8_shot_cycle.dbd
acq400ioc_DBD += acq400_judgement.dbd
acq400ioc_DBD += sodTimeout.dbd
acq400ioc_DBD += select_awg_distributor.dbd
acq400ioc_DBD += judge_win_clr_all.dbd
acq400ioc_DBD += pg_trg_debounce.dbd
acq400ioc_DBD += wrs_coldboot_pwr_handshake.dbd
acq400ioc_DBD += rtm_buffer_mon.dbd
acq400ioc_DBD += mgt_ssb.dbd
acq400ioc_DBD += slowmon_rate_adjust.dbd
acq400ioc_DBD += hudpResetOnStop.dbd
acq400ioc_DBD += continuous_wdg.dbd
acq400ioc_DBD += sfp_txen.dbd
acq400ioc_DBD += ppw_tick_scaler.dbd

ifdef STUBPVA
$(info PVA NOT INCLUDED)
else
# PVAccess
$(info PVA IS INCLUDED define STUBPVA=1 to exclude)
acq400ioc_DBD += qsrv.dbd
acq400ioc_DBD += PVAServerRegister.dbd
acq400ioc_LIBS += qsrv
acq400ioc_LIBS += $(EPICS_BASE_PVA_CORE_LIBS)
endif

# Add all the support libraries needed by this IOC
acq400ioc_LIBS += acq2ioc
acq400ioc_LIBS += seq pv
acq400ioc_LIBS += acq

# acq400ioc_registerRecordDeviceDriver.cpp derives from acq400ioc.dbd
acq400ioc_SRCS += acq400ioc_registerRecordDeviceDriver.cpp
acq400ioc_SRCS += acq400_judgement.cpp


#acq400ioc_SRCS += sncExample.st
acq400ioc_SRCS += autoRepeat.st
acq400ioc_SRCS += aoRangeSet.st
acq400ioc_SRCS += aoRangeSet424.st
acq400ioc_SRCS += acq43x_setSampleRate.st
acq400ioc_SRCS += acq43x_setSampleRateIntClk.st
acq400ioc_SRCS += onSetTransient.st
acq400ioc_SRCS += mgtStopOnLinkDown.st
acq400ioc_SRCS += calmon.st
acq400ioc_SRCS += calmonAO.st
acq400ioc_SRCS += calmon42x.st
acq400ioc_SRCS += calmonBOLO.st
acq400ioc_SRCS += calmon480.st
acq400ioc_SRCS += calmonSC32.st
acq400ioc_SRCS += setMB_ClockMonitor.st
acq400ioc_SRCS += v2f_cal.st
acq400ioc_SRCS += pvmirror.st
acq400ioc_SRCS += on_delay.st
acq400ioc_SRCS += clk_freq_flasher.st
acq400ioc_SRCS += pg4_flasher.st
acq400ioc_SRCS += sc32_gain_mux.st
acq400ioc_SRCS += sc32_autozero.st
acq400ioc_SRCS += atd_range_set.st
acq400ioc_SRCS += shot_busy.st
acq400ioc_SRCS += wr_clk_mon.st
acq400ioc_SRCS += badledfixer.st
acq400ioc_SRCS += mgt8_shot_cycle.st
acq400ioc_SRCS += sod_timeout.st
acq400ioc_SRCS += select_awg_distributor.st
acq400ioc_SRCS += judge_win_clr_all.st
acq400ioc_SRCS += pg_trg_debounce.st
acq400ioc_SRCS += wrs_coldboot_pwr_handshake.st
acq400ioc_SRCS += rtm_buffer_mon.st
acq400ioc_SRCS += mgt_ssb.st
acq400ioc_SRCS += slowmon_rate_adjust.st
acq400ioc_SRCS += hudpResetOnStop.st
acq400ioc_SRCS += continuous_wdg.st
acq400ioc_SRCS += sfp_txen.st
acq400ioc_SRCS += ppw_tick_scaler.st

# Build the main IOC entry point on workstation OSs.
acq400ioc_SRCS_DEFAULT += acq400iocMain.cpp \
    AcqHostDescr.cpp AcqHostDevice.cpp \
    devAiAcqHost.cpp AcqAiHostDescr.cpp \
    devWfAcqHost.cpp AcqWfHostDescr.cpp AcqWfCalc.cpp \
    devBiAcqHost.cpp AcqBiHostDescr.cpp \
    devBoAcqHost.cpp AcqBoHostDescr.cpp \
    devLiAcqHost.cpp AcqLiHostDescr.cpp \
    devLoAcqHost.cpp AcqLoHostDescr.cpp \
    devMbbiAcqHost.cpp AcqMbbiHostDescr.cpp \
    devMbboAcqHost.cpp AcqMbboHostDescr.cpp \
    devWfAWGHost.cpp AcqWfAWGHostDescr.cpp \
    devBoAcqCommand.cpp AcqBoCommandDescr.cpp \
    acq400_caldata.cpp \
    tinyxml2.cpp \
    FileMonitor.cpp VFile.cpp  \
    subThreadSleep.c
    

acq400ioc_SRCS_linux-arm += bollocks.cpp

acq400ioc_SRCS_vxWorks += -nil-

# Add support from base/src/vxWorks if needed
#acq400ioc_OBJS_vxWorks += $(EPICS_BASE_BIN)/vxComLibrary

# Finally link to the EPICS Base libraries
acq400ioc_LIBS += $(EPICS_BASE_IOC_LIBS)

PROD_SYS_LIBS_DEFAULT += stream asyn pcre fftw3f
#===========================

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD RULES AFTER THIS LINE

