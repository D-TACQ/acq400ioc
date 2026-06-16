/* bolo_button.st
 * activate bolo modes based on front panel button presses
 * */

program bolo_button

/*
 * +r to make the generated code reentrant, 
 * thus allowing more than one instance of the program to run on an IOC.
 */
option +r;

/*
 * +m to include the main procedure (seqMain.c) for a standalone program.
 */
/* option +m; */

%%#include <stdio.h>
%%#include <stdlib.h>

/*
 * The mode is determined by the counts of the trigger and sync counters
 * */
int mode; assign mode to "{uut}:{site}:SIG:EVT_EXT:COUNT";
monitor mode;

#define MODE_IDLE  0
#define MODE_CALIB 1
#define MODE_RUN   2

int calib_button; assign calib_button to "{uut}:{site}:SIG:TRG_EXT:COUNT";
monitor calib_button;

int run_button; assign run_button to "{uut}:{site}:SIG:SYN_EXT:COUNT";
monitor run_button;


/*
 * run_calibfit is part of the BOLODSP package
 * set_arm is the garden variety way of arming an ACQ400
 * it will then capture on trigger
 *
 * TODO: Put in some logic in case these files do not exist
 * if (file_not_exist) { tell user bolo package not enabled }
 */
string calib_script = "/usr/local/bin/run_calibfit";
string run_script = "/usr/local/bin/set_arm";

int verbose;

/* monitor previous state */
int calib_button0 = 1;
int run_button0 = 1;

int site;
char* message;
int rc;

ss bolo_button_states {
	state init {
		when() {
			if (macValueGet("verbose")){
				verbose = macValueGet("verbose")[0] - '0';
			}
			site = macValueGet("site")[0] - '0';
		} state idle
	}
	
	state idle {
		entry {
			//bypass_debounce = 1;
			//pvPut(bypass_debounce);
			if (verbose){
				printf("in idle state on site %d \n", site);
			}
		}

                when(calib_button > calib_button0) {
                    calib_button0 = calib_button;
                } state calib

                when(run_button > run_button0) {
                    run_button0 = run_button;
                } state run

		when {
			
		} state idle
	}

	state calib {
		entry {
			// bypass_debounce = 1;
			// pvPut(bypass_debounce);
                        rc = system(calib_script);
			if (verbose){
				printf("in calib state on site %d \n", site);
			}
		}
		when() {
		} state idle
	}
	state run {
		entry {
			//bypass_debounce = 1;
			//pvPut(bypass_debounce);
                        rc = system(run_script);
			if (verbose){
				printf("in run state on site %d \n", site);
			}
		}
		when {
			
		} state idle
	}
}
