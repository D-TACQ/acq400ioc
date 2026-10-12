/* ------------------------------------------------------------------------- */
/* acq400_caldata.cpp acq400ioc						     */
/*
 * acq400_caldata.cpp
 *
 *  Created on: 12 May 2015
 *      Author: pgm
 */

/* ------------------------------------------------------------------------- */
/*   Copyright (C) 2015 Peter Milne, D-TACQ Solutions Ltd                    *
 *                      <peter dot milne at D hyphen TACQ dot com>           *
 *                                                                           *
 *  This program is free software; you can redistribute it and/or modify     *
 *  it under the terms of Version 2 of the GNU General Public License        *
 *  as published by the Free Software Foundation;                            *
 *                                                                           *
 *  This program is distributed in the hope that it will be useful,          *
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of           *
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            *
 *  GNU General Public License for more details.                             *
 *                                                                           *
 *  You should have received a copy of the GNU General Public License        *
 *  along with this program; if not, write to the Free Software              *
 *  Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.                */
/* ------------------------------------------------------------------------- */

#include <stdio.h>
#include <assert.h>
#include "acq-util.h"
#include "tinyxml2.h"

extern "C" {
	void* acq400_openDoc(const char* docfile, int* nchan);
	int acq400_isCalibrated(void* prv);
	int acq400_cal_ll_check_success(int site, int gains[], int nchan);
	int acq400_getChannel(void *prv, int ch, const char* sw, float* eslo, float* eoff, int nocal);
	int acq400_getChannelByNearestGain(void *prv, int ch, const char* sw, int gain, float* eslo, float* eoff, int nocal);
	int acq400_isData32(void* prv);
};

static int verbose = ::getenv_default("CALDATA_VERBOSE", 0);

#define VPRINTF if (verbose) printf

using namespace tinyxml2;

#define RETNULL do { printf("ERROR %d\n", __LINE__); return 0; } while(0)

#define RETERRNULL(node2, node1, key) \
	if (((node2) = (node1)->FirstChildElement(key)) == 0){\
		printf("acq400_openDoc() ERROR:%d\n", __LINE__); \
		return 0;\
	}

void* acq400_openDoc(const char* docfile, int* nchan)
{
	printf("acq400_openDoc(%s)\n", docfile);


	XMLDocument* doc = new XMLDocument;
	XMLError rc = doc->LoadFile(docfile);

	if (rc != XML_NO_ERROR){
		printf("ERROR:%d\n", rc);
		return 0;
	}
	XMLNode* node;

	RETERRNULL(node, doc, "ACQ");
	RETERRNULL(node, node, "AcqCalibration");
	RETERRNULL(node, node, "Info");
	RETERRNULL(node, node, "SerialNum");

	XMLText* snum = node->FirstChild()->ToText();


	RETERRNULL(node, doc, "ACQ");
	RETERRNULL(node, node, "AcqCalibration");
	RETERRNULL(node, node, "Data");
	rc = node->ToElement()->QueryIntAttribute("AICHAN", nchan);
	if (rc == XML_NO_ERROR){
		printf("Docfile:%s Serialnumber:%s AICHAN:%d\n",
				docfile, snum->Value(), *nchan);
		return doc;
	}else{
		printf("ERROR getting AICHAN %d\n", rc);
		return 0;
	}
}

static int set_values(XMLElement *chdef, float* eslo, float* eoff)
{
	if (chdef->QueryFloatAttribute("eslo", eslo) != 0) RETNULL;
	if (chdef->QueryFloatAttribute("eoff", eoff) != 0) RETNULL;
	return 1;
}
static int _acq400_getChannel(XMLNode *range, int ch, float* eslo, float* eoff, int nocal)
{
	if (!nocal){
		/* search calibrated */
		for (XMLNode *cch = range->FirstChildElement("Calibrated"); cch;
				cch = cch->NextSibling()){
			int this_ch = -1;
			if (cch->ToElement()->QueryIntAttribute("ch", &this_ch) == 0 && this_ch == ch){
				return set_values(cch->ToElement(), eslo, eoff);
			}
		}
	}
	XMLElement *nominal = range->FirstChildElement("Nominal");
	if (!nominal) RETNULL;
	return set_values(nominal, eslo, eoff);
	return 0;
}

#define RETERRNULL(node2, node1, key) \
	if (((node2) = (node1)->FirstChildElement(key)) == 0){\
		printf("acq400_openDoc() ERROR:%d\n", __LINE__); \
		return 0;\
	}

int acq400_isCalibrated(void *prv)
/** return 0: default (no cal file), 1: cal file with range defaults but uncalibrated  2: calibrated */
{
	if (prv == 0){
		return 0;
	}
	XMLDocument* doc = static_cast<XMLDocument*>(prv);
	XMLNode* node;
	RETERRNULL(node, doc, "ACQ");
	RETERRNULL(node, node, "AcqCalibration");
	RETERRNULL(node, node, "Data");
	RETERRNULL(node, node, "Range");
	if (node->FirstChildElement("Calibrated")){
		return 2;
	}else{
		return 1;
	}
}
int acq400_isData32(void* prv)
{
	XMLDocument* doc = static_cast<XMLDocument*>(prv);
	XMLNode* node;
	int code_max;

	RETERRNULL(node, doc, "ACQ");
	RETERRNULL(node, node, "AcqCalibration");
	RETERRNULL(node, node, "Data");
	XMLError rc =  node->ToElement()->QueryIntAttribute("code_max", &code_max);

	if (rc == XML_NO_ERROR){
		return code_max > 65535;
	}else{
		printf("ERROR getting code_max %d\n", rc);
		return 0;
	}
}

int _acq400_getChannelTop(void *prv, int ch, const char* sw, float* eslo, float* eoff, int nocal, XMLNode **range=0)
{
	XMLDocument* doc = static_cast<XMLDocument*>(prv);

	XMLNode* node;

	VPRINTF("%s ch:%d sw:%s 01\n", __FUNCTION__, ch, sw);

	RETERRNULL(node, doc, "ACQ");
	RETERRNULL(node, node, "AcqCalibration");
	RETERRNULL(node, node, "Data");
	for (XMLNode *_range = node->FirstChildElement("Range"); _range;
			_range = _range->NextSibling()){
		const char* findkey = _range->ToElement()->Attribute("sw");
		int nosw = sw==0 || findkey==0 || strcmp(findkey, "default")==0;
		if (nosw || strcmp(sw, findkey) == 0){
			if (range){
				*range = _range;
			}
			VPRINTF("%s ch:%d sw:%s 44\n", __FUNCTION__, ch, sw);
			return _acq400_getChannel(_range, ch, eslo, eoff, nocal);
		}
	}
	printf("ERROR: ch:%d range \"%s\" not found\n", ch, sw);
	return -1;
}
int acq400_getChannel(void *prv, int ch, const char* sw, float* eslo, float* eoff, int nocal)
/* returns >0 on success */
{
	return _acq400_getChannelTop(prv, ch, sw, eslo, eoff, nocal);
}

int acq400_getChannelByNearestGain(void *prv, int ch, const char* sw, int gain, float* eslo, float* eoff, int nocal)
/* returns >0 on success, finds nearest lower gain and returns scaled eslo */
{
	XMLNode* range;

	VPRINTF("%s ch:%d sw:%s gain:%d\n", __FUNCTION__, ch, sw, gain);
	assert(gain);

	if (_acq400_getChannelTop(prv, ch, sw, eslo, eoff, nocal, &range) == -1){
		VPRINTF("%s ch:%d _acq400_getChannelTop FAIL\n", __FUNCTION__, ch);
		return -1;
	}
	int gx;
	assert(range);

	XMLError rc = range->ToElement()->QueryIntAttribute("gain", &gx);
	if (rc != XML_SUCCESS){
		printf("ERROR: gain attribute not found\n");
		return -1;
	}

	VPRINTF("%s: %.5g gx:%d\n", __FUNCTION__, *eslo, gx);
	if (gx != gain){
		*eslo /= (gain/gx);
		VPRINTF("%s: %.5g adjusted\n", __FUNCTION__, *eslo);
	}
	return 1;
}


static void fixup(int site, char* cmd, int maxcmd, const char* gainstr, const char* actstr){
	int ch = 1;
	FILE* fp;

	for (int ic = 0; gainstr[ic]; ++ic, ++ch){
		if (gainstr[ic] != actstr[ic]){
			snprintf(cmd, maxcmd, "set.site %d gain%d=%c", site, ch, gainstr[ic]);
			fp = popen(cmd, "r");
			pclose(fp);
		}
	}
}

/** @@todo: popen() causes memory stress. It's a heavy solution.
 *  better: create PV GAINS that has the same string.
 *  the string is maintained by the normal StreamDevice on the normal service socket.
 *  acq400_cal_ll_check_success is ALWAYS called from SNL, so pvGet GAINS and pass it in ..
 */
int acq400_cal_ll_check_success(int site, int gains[], int nchan)
{
	char cmd[80];
	char* actstr = cmd;
	char gainstr[33];
	FILE* fp;
	int ch;
	int rc = 0;

	for (ch = 1; ch <= nchan; ++ch){
		gainstr[ch-1] = gains[ch]+'0';
	}
	gainstr[ch-1] = '\0';

	snprintf(cmd, 80, "get.site %d gains", site);

	fp = popen(cmd, "r");
	if (fp == 0){
		char emsg[256];
		snprintf(emsg, 255, "ERROR: %s %s popen fail", __FUNCTION__, cmd);
		perror(emsg);
		rc = -1;
	}else if (fgets(actstr, 80, fp) == 0){
		rc = -1;
		pclose(fp);
	}else{
		pclose(fp);

		actstr[strlen(actstr)-1] = '\0';  /* rtrim */
		rc = strcmp(gainstr, actstr);
		printf("site:%d Compare: set:\"%s\" act:\"%s\" %s\n", site, gainstr, actstr, rc? "Needs Fixing": "OK");
		if (rc){
			fixup(site, cmd, 80, gainstr, actstr);
		}
	}

	return rc;
}
